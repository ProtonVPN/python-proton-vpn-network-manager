%define unmangled_name proton-vpn-network-manager
%define version 0.6.3
%define release 1

Prefix: %{_prefix}

Name: python3-%{unmangled_name}
Version: %{version}
Release: %{release}%{?dist}
Summary: %{unmangled_name} library

Group: ProtonVPN
License: GPLv3
Vendor: Proton Technologies AG <opensource@proton.me>
URL: https://github.com/ProtonVPN/%{unmangled_name}
Source0: %{unmangled_name}-%{version}.tar.gz
BuildArch: noarch
BuildRoot: %{_tmppath}/%{unmangled_name}-%{version}-%{release}-buildroot

BuildRequires: python3-gobject
BuildRequires: NetworkManager
BuildRequires: NetworkManager-openvpn
BuildRequires: NetworkManager-openvpn-gnome
BuildRequires: gobject-introspection
BuildRequires: python3-setuptools
BuildRequires: python3-proton-core
BuildRequires: python3-proton-vpn-logger
BuildRequires: python3-proton-vpn-api-core >= 0.33.0

Requires: python3-gobject
Requires: NetworkManager
Requires: NetworkManager-openvpn
Requires: NetworkManager-openvpn-gnome
Requires: gobject-introspection
Requires: python3-setuptools
Requires: python3-proton-core
Requires: python3-proton-vpn-logger
Requires: python3-proton-vpn-api-core >= 0.33.0

Obsoletes: python3-proton-vpn-network-manager-openvpn
Obsoletes: python3-proton-vpn-network-manager-wireguard

%{?python_disable_dependency_generator}

%description
Package %{unmangled_name} library.


%prep
%setup -n %{unmangled_name}-%{version} -n %{unmangled_name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES


%files -f INSTALLED_FILES
%{python3_sitelib}/proton/
%{python3_sitelib}/proton_vpn_network_manager-%{version}*.egg-info/
%defattr(-,root,root)

%changelog
* Mon Sep 02 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.6.3
- Declare dependency breakage

* Fri Aug 30 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.6.2
- Force removal of obsolete packages

* Fri Aug 30 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.6.1
- Change Replaces by Conflicts clause on debian package

* Thu Aug 22 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.6.0
- Move openvpn and wireguard packages into this one

* Tue Aug 20 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.5.3
- Remove dead code

* Thu Aug 08 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.5.2
- Fix app stuck in disconnecting state on OpenVPN

* Wed Aug 07 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.5.1
- Fix app stuck in disconnecting state

* Thu Jul 11 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.5.0
- Add proton-vpn-api-core dependency

* Fri Mar 1 2024 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.4.2
- Update to new interface

* Tue Feb 27 2024 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.4.1
- Make necessary changes to support Wireguard protocol

* Wed Feb 14 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.4.0
- Initialize connection with persisted parameters

* Wed Jan 31 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.3.5
- Remove connection delay

* Wed Jan 31 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.3.4
- Initialize state machine in Error state when inactive VPN connection is found

* Thu Jan 11 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.3.3
- Fix deadlock when notifying connection subscribers

* Tue Jan 09 2024 Josep Llaneras <josep.llaneras@proton.ch> 0.3.2
- Fix connection cancellation

* Wed Dec 13 2023 Josep Llaneras <josep.llaneras@proton.ch> 0.3.1
- Fix state machine getting stuck in disconnecting state.

* Mon Sep 04 2023 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.3.0
- Add time delay before making tcpcheck call, due to kill switch, to ensure that server is reacheable 

* Wed Jul 05 2023 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.2.7
- Update Loader.get_all() argument for getting NetworkManager protocols

* Fri Apr 14 2023 Josep Llaneras <josep.llaneras@proton.ch> 0.2.6
- Test network connectivity to the server before starting the VPN connection

* Mon Apr 03 2023 Josep Llaneras <josep.llaneras@proton.ch> 0.2.5
- Adapt to VPN connection refactoring

* Thu Feb 09 2023 Josep Llaneras <josep.llaneras@proton.ch> 0.2.4
- Log exception when trying to connect and the network interface is not available

* Fri Dec 30 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.2.3
- Remove network manager connection when the VPN connection is stopped

* Wed Dec 21 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.2.2
- Do not leak NetworkManager connections on connection setup errors

* Tue Dec 20 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.2.1
- Handle errors happening while setting up or starting the connection
- Split stop_connection in 2: stop_connection and remove_connection
- Ovewrite remove_persistence so that it also removes the NM connection

* Wed Dec 14 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.2.0
- Handle device disconnected event

* Fri Dec 02 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.1.0
- Add persisted connection parameters to connection state

* Fri Nov 4 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.0.2
- Set up connection asynchronously
- Run a single separate main loop for NM client

* Wed Jun 1 2022 Proton Technologies AG <opensource@proton.me> 0.0.1
- First RPM release
