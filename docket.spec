%global _docketdir /opt/rocknsm/docket

Name:           docket
Version:        0.0.4
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
cp -a systemd/docket-tmpfiles.conf %{buildroot}/%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-uwsgi.socket  %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-celery.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-tmpfiles.conf %{buildroot}%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.ini %{buildroot}%{_sysconfdir}/rocknsm/
install -p -m 644 systemd/docket.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -p -m 644 systemd/docket.preset %{buildroot}%{_presetdir}/95-%{name}.preset

%pre
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd USERNAME >/dev/null || \
    useradd -r -g %{name} -d %{_docketdir} -s /sbin/nologin \
    -c "System account for Docket services for ROCK NSM" %{name}
exit 0

%post
%systemd_post docket-celery.service
%systemd_post docket-uwsgi.socket
%systemd_post docket-uwsgi.service


%preun
%systemd_preun docket-celery.service

%postun
%systemd_postun_with_restart docket-celery.service


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

%doc README.md LICENSE 
%doc contrib/nginx-example.conf

%changelog
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

