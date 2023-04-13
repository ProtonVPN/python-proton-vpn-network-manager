"""
Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class VPNServer:
    server_ip: str = None
    udp_ports: List[int] = None
    tcp_ports: List[int] = None
    wg_public_key_x25519: str = None
    domain: str = None
    servername: str = None


@dataclass
class VPNPubKeyCredentials:
    certificate_pem: str = None
    wg_private_key: str = None
    openvpn_private_key: str = None


@dataclass
class VPNUserPassCredentials:
    username: str = None
    password: str = None


@dataclass
class VPNCredentials:
    pubkey_credentials: VPNPubKeyCredentials = None
    userpass_credentials: VPNUserPassCredentials = None


@dataclass
class Features:
    netshield: int = 0
    vpn_accelerator: bool = True
    port_forwarding: bool = False
    random_nat: bool = True
    safe_mode: bool = False


@dataclass
class Settings:
    dns_custom_ips: List[str] = field(default_factory=lambda: [])
    split_tunneling_ips: List[str] = field(default_factory=lambda: [])
    ipv6: bool = False
    features: Features = field(default_factory=lambda: Features())
