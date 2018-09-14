%global _docketdir /opt/rocknsm/docket

%if 0%{?epel}
%define scl rh-nodejs8
%define scl_prefix rh-nodejs8-
%endif

Name:           docket
Version:        1.0.1
Release:        3
Summary:        A Python HTTP API for Google Stenographer

License:        BSD
URL:            http://rocknsm.io/
Source0:        https://github.com/rocknsm/%{name}/archive/%{name}-%{version}-1.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python-devel
%{?systemd_requires}
BuildRequires:  systemd
BuildRequires:  %{?scl_prefix}npm
Requires(pre):  shadow-utils

Requires:       python2-flask
Requires:       python2-flask-restful
Requires:       python2-celery
Requires:       python-redis
Requires:       python-requests
Requires:       python2-tonyg-rfc3339

Requires:       uwsgi
Requires:       uwsgi-plugin-python2

Requires:       wireshark
Requires:       redis

%description
Docket provides an HTTP API layer for Google Stenographer, allowing RESTful API access to indexed PCAP. Docket is written in Python and uses the veritable Flask framework.

%prep
%setup -q

%build
cd frontend

%{?scl:scl enable %{scl} "}
# Build ReactJS frontend
npm install
npm run build
%{?scl: "}

%install
rm -rf %{buildroot}
DESTDIR=%{buildroot}

# make directories
mkdir -p %{buildroot}/%{_sysconfdir}/{docket,sysconfig}
mkdir -p %{buildroot}/%{_docketdir}
mkdir -p %{buildroot}/%{_docketdir}/docket
mkdir -p %{buildroot}/%{_docketdir}/frontend
mkdir -p %{buildroot}/%{_tmpfilesdir}
mkdir -p %{buildroot}/%{_unitdir}
mkdir -p %{buildroot}/%{_presetdir}
mkdir -p %{buildroot}/%{_localstatedir}/log/%{name}

# Install docket files
cp -a docket/. %{buildroot}/%{_docketdir}/docket/.
cp -a conf/. %{buildroot}/%{_sysconfdir}/docket/.
install -p -m 644 systemd/docket.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket.socket  %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-celery-query.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-celery-io.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-tmpfiles.conf %{buildroot}%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.ini %{buildroot}%{_sysconfdir}/docket/
install -p -m 644 systemd/docket.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -p -m 644 systemd/docket.preset %{buildroot}%{_presetdir}/95-%{name}.preset

# Install frontend
cp -a frontend/dist/. %{buildroot}/%{_docketdir}/frontend/.

install -d -m 0755 %{buildroot}/run/%{name}/
install -d -m 0755 %{buildroot}%{_localstatedir}/spool/%{name}/

touch %{buildroot}/run/%{name}/%{name}.socket
touch %{buildroot}/%{_localstatedir}/log/%{name}/%{name}.log

%pre
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd %{name} >/dev/null || \
    useradd -r -g %{name} -d %{_docketdir} -s /sbin/nologin \
    -c "System account for Docket services for ROCK NSM" %{name}
exit 0

%post
%systemd_post docket.socket docket.service docket-celery-query.service docket-celery-io.service

%preun
%systemd_preun docket.socket docket.service docket-celery-query.service docket-celery-io.service

%postun
%systemd_postun_with_restart docket.socket docket.service docket-celery-query.service docket-celery-io.service

%files
%defattr(0644, root, root, 0755)
%dir %{_docketdir}
%{_docketdir}/*

# Config files
%config %{_sysconfdir}/docket/*.yaml
%config %{_sysconfdir}/docket/docket-uwsgi.ini

# Service files
%{_tmpfilesdir}/%{name}.conf
%{_unitdir}/*
%{_presetdir}/*
%{_sysconfdir}/sysconfig/%{name}

# Runtime dirs
%dir /run/%{name}/
%attr(-,docket,docket) /run/%{name}/
%dir %{_localstatedir}/spool/%{name}/
%attr(-,docket,docket) %{_localstatedir}/spool/%{name}/
%dir %{_localstatedir}/log/%{name}/
%attr(-,docket,docket) %{_localstatedir}/log/%{name}/

# Add the systemd socket so it's removed on uninstall
%ghost /run/%{name}/%{name}.socket
%ghost %{_localstatedir}/log/%{name}/%{name}.log

%doc README.md LICENSE.txt docs/
%doc contrib/nginx-example.conf
%doc contrib/docket_lighttpd_scgi.conf
%doc contrib/docket_lighttpd_vhost.conf

%changelog
* Fri Feb 23 2018 Derek Ditch <derek@rocknsm.io> 1.0.1-3
- Fixed LICENSE in spec file (derek@rocknsm.io)
- Allows for easy push directly to Copr :magic: (derek@rocknsm.io)

* Fri Feb 23 2018 Derek Ditch <derek@rocknsm.io> 1.0.1-2
- Fixed typo in the log path (derek@rocknsm.io)

* Fri Feb 23 2018 Derek Ditch <derek@rocknsm.io> 1.0.0-1
- Better concurrency & new UI (#22)
- Update docket configuration path (#17) (anlx-sw@users.noreply.github.com)
- Checked in Vagrantfile for testing (derek@rocknsm.io)
- Lots of bugs squashed. Probably more introduced. ¯\_(ツ)_/¯

* Mon Jan 08 2018 Jeffrey Kwasha <JeffKwasha@users.noreply.github.com> 0.2.1-1
- Requests are queued to improve stenographer performance and squash docket CPU spikes
- Queries now return JSON: query, id, url where the capture will be created, queue time.
- Parallelized queries to stenographer instances
- New API: /urls - a JSON dictionary of id : url for all available captures
- New API: /ids - a JSON list of ids for active and completed queries
- New API: /status - JSON: the state of active and completed queries
- New API: /cleanup - ignores CLEANUP_PERIOD and runs immediately
- New GUI: /gui - an HTML form with a dynamic stack of queries made with links
- More helpful error messages and better 'front-end' request validation.
- improved cleanup - query expiration is configurable by time, free space, frequency
- improved logging and error handling
- config options now understand 'capacity' ('2MB') and 'duration' ('30s') depending on the option
- Result captures are served directly by nginx

* Fri Dec 01 2017 Derek Ditch <derek@rocknsm.io> 0.1.1-1
- Fixes lingering permission issues with systemd. (derek@rocknsm.io)

* Wed Nov 22 2017 Derek Ditch <derek@rocknsm.io> 0.1.0-1
- Ansible role under contrib/rocknsm.docket now deploys docket
- Ansible role currently supports lighttpd and configs stenographer keys

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
