#!/usr/bin/env python3
'''
This program generates a deb changelog file, and rpm spec file and a
CHANGELOG.md file for this project.

It reads versions.yml.
'''
import os
import yaml
import devtools.versions as versions

# The root of this repo
ROOT = os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))
)

NAME      = "protonvpn-network-manager"  # Name of this application.
VERSIONS  = os.path.join(ROOT, "versions.yml")  # Name of this applications versions.yml
RPM       = os.path.join(ROOT, "rpmbuild", "SPECS", "package.spec")  # Path of spec filefor rpm.
DEB       = os.path.join(ROOT, "debian", "changelog")  # Path of debian changelog.
MARKDOWN  = os.path.join(ROOT, "CHANGELOG.md",)  # Path of CHANGELOG.md.

# The template for the rpm spec file.
#
SPEC_TEMPLATE='''%define unmangled_name proton-vpn-network-manager
%define version {version}
%define release 1

Prefix: %{{_prefix}}

Name: python3-%{{unmangled_name}}
Version: %{{version}}
Release: %{{release}}%{{?dist}}
Summary: %{{unmangled_name}} library

Group: ProtonVPN
License: GPLv3
Vendor: Proton AG <opensource@proton.me>
URL: https://github.com/ProtonVPN/python-%{{unmangled_name}}
Source0: %{{unmangled_name}}-%{{version}}.tar.gz
BuildArch: noarch
BuildRoot: %{{_tmppath}}/%{{unmangled_name}}-%{{version}}-%{{release}}-buildroot

BuildRequires: python3-gobject
BuildRequires: NetworkManager
BuildRequires: NetworkManager-openvpn
BuildRequires: NetworkManager-openvpn-gnome
BuildRequires: gobject-introspection
BuildRequires: python3-setuptools
BuildRequires: python3-proton-core
BuildRequires: python3-proton-vpn-api-core >= 0.35.6
BuildRequires: python3-proton-vpn-local-agent >= 1.1.0

Requires: python3-gobject
Requires: NetworkManager
Requires: NetworkManager-openvpn
Requires: NetworkManager-openvpn-gnome
Requires: gobject-introspection
Requires: python3-setuptools
Requires: python3-proton-core
Requires: python3-proton-vpn-api-core >= 0.35.6
Requires: python3-proton-vpn-local-agent >= 1.1.0

Conflicts: python3-proton-vpn-network-manager-openvpn < 0.1.1
Conflicts: python3-proton-vpn-network-manager-wireguard < 0.4.7
Conflicts: python3-proton-vpn-killswitch-network-manager < 0.6.1
Conflicts: python3-proton-vpn-killswitch-network-manager-wireguard < 0.2.1

Obsoletes: python3-proton-vpn-network-manager-openvpn
Obsoletes: python3-proton-vpn-network-manager-wireguard
Obsoletes: python3-proton-vpn-killswitch-network-manager
Obsoletes: python3-proton-vpn-killswitch-network-manager-wireguard

%{{?python_disable_dependency_generator}}

%description
Package %{{unmangled_name}} library.


%prep
%setup -n %{{unmangled_name}}-%{{version}} -n %{{unmangled_name}}-%{{version}}

%build
python3 setup.py build

%install
python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES


%files -f INSTALLED_FILES
%{{python3_sitelib}}/proton/
%{{python3_sitelib}}/proton_vpn_network_manager-%{{version}}*.egg-info/
%defattr(-,root,root)

%changelog'''


def build():
    '''
    This is what generates the rpm spec, deb changelog and
    markdown CHANGELOG.md file.
    '''
    with open(VERSIONS, encoding="utf-8") as versions_file:

        # Load versions.yml
        versions_yml = list(yaml.safe_load_all(versions_file))

        # Make our files
        versions.build_rpm(RPM,      versions_yml, SPEC_TEMPLATE)
        versions.build_deb(DEB,      versions_yml, NAME)
        versions.build_mkd(MARKDOWN, versions_yml)


if __name__ == "__main__":
    build()
