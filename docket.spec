%global _docketdir /opt/rocknsm/docket

Name:           docket
Version:        0.0.4
Release:        1%{?dist}
Summary:        A Python HTTP API for Google Stenographer

License:        BSD
URL:            http://rocknsm.io/
Source0:        https://github.com/rocknsm/%{name}/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python-devel
BuildRequires:  systemd

Requires:       python2-flask
Requires:       python2-flask-restful
Requires:       python-flask-script
Requires:       python2-celery
Requires:       python-redis
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

# Install docket files
cp -a docket/. %{buildroot}/%{_docketdir}/docket/.
cp -a conf/. %{buildroot}/%{_docketdir}/conf/.
cp -a systemd/docket-tmpfiles.conf %{buildroot}/%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.service %{buildroot}/%{_unitdir}/
install -p -m 644 systemd/docket-uwsgi.socket  %{buildroot}/%{_unitdir}/
install -p -m 644 systemd/docket-celery.service %{buildroot}/%{_unitdir}/
install -p -m 644 systemd/docket-tmpfiles.conf %{buildroot}/%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.ini %{buildroot}/%{_sysconfdir}/rocknsm/
install -p -m 644 systemd/docket.sysconfig %{buildroot}/%{_sysconfdir}/sysconfig/docket

%files
%defattr(0644, root, root, 0755)
%dir %{_docketdir}/
%dir %{_docketdir}/conf
%dir %{_docketdir}/docket
%dir %{_docketdir}/docket/common
%dir %{_docketdir}/docket/resources
%{_docketdir}/*
%{_docketdir}/conf/*
%{_docketdir}/docket/*
%{_docketdir}/docket/common/*
%{_docketdir}/docket/resources

# Service files

%{_tmpfilesdir}/%{name}.conf

%doc README.md LICENSE
%config %{_docketdir}/conf/devel.yaml

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

