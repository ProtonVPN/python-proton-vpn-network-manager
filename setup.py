#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="python-protonvpn-network-manager",
    version="0.0.0",
    description="Proton Technologies VPN connector for linux",
    author="Proton Technologies",
    author_email="contact@protonmail.com",
    url="https://github.com/ProtonVPN/pyhon-protonvpn-network-manager",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["proton-core"],
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
