%global _docketdir /opt/rocknsm/docket

Name:           docket
Version:        0.2.1
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
mkdir -p %{buildroot}/%{_docketdir}/docket
mkdir -p %{buildroot}/%{_tmpfilesdir}
mkdir -p %{buildroot}/%{_unitdir}
mkdir -p %{buildroot}/%{_presetdir}

# Install docket files
cp -a docket/. %{buildroot}/%{_docketdir}/docket/.
cp -a conf/. %{buildroot}/%{_docketdir}/conf/.
install -p -m 644 systemd/docket.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket.socket  %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-celery-query.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-celery-io.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/docket-tmpfiles.conf %{buildroot}%{_tmpfilesdir}/%{name}.conf
install -p -m 644 systemd/docket-uwsgi.ini %{buildroot}%{_sysconfdir}/rocknsm/
install -p -m 644 systemd/docket.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -p -m 644 systemd/docket.preset %{buildroot}%{_presetdir}/95-%{name}.preset

install -d -m 0755 %{buildroot}/run/%{name}/
install -d -m 0755 %{buildroot}%{_localstatedir}/spool/%{name}/

touch %{buildroot}/run/%{name}/%{name}.socket

%pre
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd %{name} >/dev/null || \
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
%doc contrib/docket_lighttpd_scgi.conf
%doc contrib/docket_lighttpd_vhost.conf

%changelog
* Mon Jan 08 2018 Jeffrey Kwasha <JeffKwasha@users.noreply.github.com> 0.2.1-1
- New API: /status - JSON describing the state of queries known by the system.
- internalized cleanup - query expiration is configurable by time or free space. 
- improved logging.  Requester's IP, port and user agent are logged.
- More helpful error messages and better 'front-end' request validation.
- configuration options now understand 'capacity' strings (KB MB GB TB PB) so: '1GB', '5MB 500KB', '1KB 1MB 1TB 0.1PB'
- configuration options now understand 'duration' strings exactly like query durations: '1h' '30s' '20m' 
- WEIGHT_* - an experimental limitation on query requests to prevent overly-burdensome requests.
- FREE_BYTES - capacity: capture query requests will be denied if the SPOOL_DIR doesn't have this much space
- FREE_NODES - integer: query requests denied if the SPOOL_DIR doesn't have this many nodes
- EXPIRE_SPACE - capacity: queries will be deleted during a cleanup to ensure this much space
- EXPIRE_TIME - duration: queries older than this will be deleted during a cleanup 
- CLEANUP_PERIOD - duration: maximum frequency of cleanup
- LOG_* - Logging options are now configurable
- LOG_FILE - works better, but it's far from perfect
- a tiny sad attempt at unittest

* Sun Dec 06 2017 Jeffrey Kwasha <JeffKwasha@users.noreply.github.com> 0.2.0-1
- Add design doc (JeffKwasha@users.noreply.github.com)
- New query module for new Query and QueryRequest classes (JeffKwasha@users.noreply.github.com)
- New config module centralizing access to configuration parameters (JeffKwasha@users.noreply.github.com)
- Celery now uses 'query' and 'io' queues with separate workers (1 process each) to handle requests (JeffKwasha@users.noreply.github.com)
- Reduced CPU usage. Docket will not burn a core waiting for stenographer responses (JeffKwasha@users.noreply.github.com)
- Requests to several stenographer instances run in parallel (JeffKwasha@users.noreply.github.com)
- Multiple requests to a single stenographer instances will run serially to prevent IO thrashing (JeffKwasha@users.noreply.github.com)
- Merged result captures are served directly by nginx (JeffKwasha@users.noreply.github.com)
- New API: /urls - a JSON encoded dictionary of id:url for all available captures (JeffKwasha@users.noreply.github.com)
- New API: /ids - a JSON encoded list of ids for all requests (currently doesn't include requests queued for stenographer) (JeffKwasha@users.noreply.github.com)
- Queries now return a JSON encoded id, time (epoch), url where the capture file can eventually be retrieved (JeffKwasha@users.noreply.github.com)
- Duplicate queries (identical clauses within the same minute) are detected and simply refresh the expiration time (JeffKwasha@users.noreply.github.com)
- New Configuration parameters: WEB_ROOT, MERGED_NAME, IDLE_TIME, IDLE_SLEEP, IDLE_TIMEOUT, QUERY_TIMEOUT (JeffKwasha@users.noreply.github.com)

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
