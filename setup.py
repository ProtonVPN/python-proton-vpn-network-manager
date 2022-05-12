#!/usr/bin/env python

from setuptools import setup, find_namespace_packages
from pkg_resources import get_distribution
from subprocess import check_output

pkg_name="proton-vpn-network-manager"
command = 'git describe --tags --long --dirty'

def format_version():
    try:
        version = check_output(command.split()).decode('utf-8').strip()
        parts = version.split('-')
        assert len(parts) in (3, 4)
        tag, count, sha = parts[:3]
        return f"{tag}-dev{count}+{sha.lstrip('g')}"
    except:
        version = get_distribution(pkg_name).version
        return version

setup(
    name=pkg_name,
    version=format_version(),
    description="Proton Technologies VPN connector for linux",
    author="Proton Technologies",
    author_email="contact@protonmail.com",
    url="https://github.com/ProtonVPN/pyhon-protonvpn-network-manager",
    packages=find_namespace_packages(include=['proton.vpn.backend.linux.networkmanager', 'proton.vpn.backend.linux.networkmanager.dbus']),
    include_package_data=True,
    install_requires=["proton-core","proton-vpn-connection"],
    entry_points={
        "proton_loader_backend": [
            "networkmanager = proton.vpn.backend.linux.networkmanager:LinuxNetworkManager",
        ]
    },
    license="GPLv3",
    platforms="OS Independent",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python",
        "Topic :: Security",
    ]
)
