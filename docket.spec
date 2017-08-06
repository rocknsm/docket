%global _docketdir /opt/rocknsm/docket

Name:           docket
Version:        0.0.14
Release:        1%{?dist}
Summary:        A Python HTTP API for Google Stenographer

License:        BSD
URL:            http://rocknsm.io/
Source0:        https://github.com/rocknsm/%{name}/archive/%{name}-%{version}-1.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python-devel
%{?systemd_requires}
BuildRequires:  systemd
Requires(pre):  shadow-utils

Requires:       python2-flask
Requires:       python2-flask-restful
Requires:       python-flask-script
Requires:       python2-celery
Requires:       python-redis
Requires:       python-requests
Requires:       python2-tonyg-rfc3339

Requires:       uwsgi
Requires:       uwsgi-plugin-python

Requires:       wireshark
Requires:       redis

%description
Docket provides an HTTP API layer for Google Stenographer, allowing RESTful API access to indexed PCAP. Docket is written in Python and uses the veritable Flask framework.

%prep
%setup -q

%build
# Nothing to do here

%install
rm -rf %{buildroot}
DESTDIR=%{buildroot}

# make directories
mkdir -p %{buildroot}/%{_sysconfdir}/{rocknsm,sysconfig}
mkdir -p %{buildroot}/%{_docketdir}
mkdir -p %{buildroot}/%{_docketdir}/conf
mkdir -p %{buildroot}/%{_docketdir}/docket
mkdir -p %{buildroot}/%{_tmpfilesdir}
mkdir -p %{buildroot}/%{_unitdir}
mkdir -p %{buildroot}/%{_presetdir}

# Install docket files
cp -a docket/. %{buildroot}/%{_docketdir}/docket/.
cp -a conf/. %{buildroot}/%{_docketdir}/conf/.
install -p -m 644 systemd/docket.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket.socket  %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-celery.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-tmpfiles.conf %{buildroot}%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.ini %{buildroot}%{_sysconfdir}/rocknsm/
install -p -m 644 systemd/docket.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -p -m 644 systemd/docket.preset %{buildroot}%{_presetdir}/95-%{name}.preset

install -d -m 0755 %{buildroot}/run/%{name}/
install -d -m 0755 %{buildroot}%{_localstatedir}/spool/%{name}/

touch %{buildroot}/run/%{name}/%{name}.socket

%pre
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd USERNAME >/dev/null || \
    useradd -r -g %{name} -d %{_docketdir} -s /sbin/nologin \
    -c "System account for Docket services for ROCK NSM" %{name}
exit 0

%post
%systemd_post docket.socket docket.service docket-celery.service

%preun
%systemd_preun docket.socket docket.service docket-celery.service

%postun
%systemd_postun_with_restart docket.socket docket.service docket-celery.service

%files
%defattr(0644, root, root, 0755)
%dir %{_docketdir}
%config %{_docketdir}/conf/devel.yaml
%{_docketdir}/*

# Service files
%{_tmpfilesdir}/%{name}.conf
%{_unitdir}/*
%{_presetdir}/*
%{_sysconfdir}/sysconfig/%{name}
%{_sysconfdir}/rocknsm/docket-uwsgi.ini

# Runtime dirs
%dir /run/%{name}/
%attr(-,docket,docket) /run/%{name}/
%dir %{_localstatedir}/spool/%{name}/
%attr(-,docket,docket) %{_localstatedir}/spool/%{name}/

# Add the systemd socket so it's removed on uninstall
%ghost /run/%{name}/%{name}.socket

%doc README.md LICENSE docs/
%doc contrib/nginx-example.conf

%changelog
* Sun Aug 06 2017 Derek Ditch <derek@rocknsm.io> 0.0.14-1
- Add docs dir to documentation (derek@rocknsm.io)

* Sun Aug 06 2017 Derek Ditch <derek@rocknsm.io> 0.0.13-1
- Changed location of anchors to fix formatting
  (dcode@users.noreply.github.com)
- Changed formating of `docs/README.md` (dcode@users.noreply.github.com)

* Sun Aug 06 2017 Derek Ditch <derek@rocknsm.io> 0.0.12-1
- Restructured the documentation slightly (derek@rocknsm.io)
- Added docs and tweaked default config (derek@rocknsm.io)

* Sat Aug 05 2017 Derek Ditch <derek@rocknsm.io> 0.0.11-1
- Nothing to see here (derek@rocknsm.io)
- Added vagrant to gitignore (derek@rocknsm.io)

* Sat Aug 05 2017 Derek Ditch <derek@rocknsm.io> 0.0.10-1
- Accidentally left blank

* Sat Aug 05 2017 Derek Ditch <derek@rocknsm.io> 0.0.9-1
- Updated socket path in nginx example (derek@rocknsm.io)

* Sat Aug 05 2017 Derek Ditch <derek@rocknsm.io> 0.0.8-1
- Adds socket to package for autoremoval (derek@rocknsm.io)
- Fixes several discrepancies with systemd socket activation vs uwsgi
  (derek@rocknsm.io)
- Some cleanup with runtime dirs (derek@rocknsm.io)
- Cleans up systemd service files, renames main service to `docket.service`.
  (derek@rocknsm.io)

* Sat Aug 05 2017 Derek Ditch <derek@rocknsm.io> 0.0.7-1
- Fixes typo in logic (derek@rocknsm.io)
* Sat Aug 05 2017 Derek Ditch <derek@rocknsm.io> 0.0.6-1
- Adds HTTP POST API supporting form-encoded and json-encoded requests
- Fixes several bugs in error handling and data parsing
* Sun Jul 30 2017 Derek Ditch <derek@rocknsm.io> 0.0.5-1
- Fixes for RPM build and systemd dependencies
* Sun Jul 30 2017 Derek Ditch <derek@rocknsm.io> 0.0.4-1
- Adds service depndency (derek@rocknsm.io)
- Adds systemd config and tweaks to RPM spec - Adds tmpfiles.d configuration
  for docket spool dir - Adds service files for celery workers and uwsgi
  configuration - Adds socket-activation for uwsgi workers - Adds environment
  file for both systemd services `/etc/sysconfig/docket` (derek@rocknsm.io)
* Thu Jul 27 2017 Derek Ditch <derek@rocknsm.io> 0.0.3-1
- Removed .spec from gitignore (derek@rocknsm.io)
* Thu Jul 27 2017 Derek Ditch <derek@rocknsm.io> 0.0.2-1
- Initial use of tito to build SRPM

