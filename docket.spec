%global _docketdir /opt/rocknsm/docket

Name:           docket
Version:        0.0.2
Release:        1%{?dist}
Summary:        A Python HTTP API for Google Stenographer

License:        BSD
URL:            http://rocknsm.io/
Source0:        https://github.com/rocknsm/%{name}/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       python2-flask
Requires:       python2-flask-restful
Requires:       python2-celery
Requires:       python2-redis
Requires:       python2-tonyg-rfc3339

%description
ROCK is a collections platform, in the spirit of Network Security Monitoring.

%prep
%setup -q

%build


%install
rm -rf %{buildroot}
DESTDIR=%{buildroot}

#make directories
mkdir -p %{buildroot}/%{_rockdir}
mkdir -p %{buildroot}/%{_rockdir}/bin
mkdir -p %{buildroot}/%{_rockdir}/playbooks

# Install ansible files
install -p -m 755 bin/deploy_rock.sh %{buildroot}/%{_rockdir}/bin/
install -p -m 755 bin/generate_defaults.sh %{buildroot}/%{_rockdir}/bin/
cp -a playbooks/. %{buildroot}/%{_rockdir}/playbooks

%files
%defattr(0644, root, root, 0755)
%{_rockdir}/playbooks/*

%doc README.md LICENSE
%config %{_rockdir}/playbooks/ansible.cfg

%attr(0755, root, root) %{_rockdir}/bin/deploy_rock.sh
%attr(0755, root, root) %{_rockdir}/bin/generate_defaults.sh

%changelog
* Thu Jul 27 2017 Derek Ditch <derek@rocknsm.io> 0.0.2-1
- Initial use of tito to build SRPM

* Thu Jun 08 2017 spartan782 <john.hall7688@hotmail.com> 2.0.5-1
- 
Tito files added.
rock.spec added.
sign_rpm.sh added. 
