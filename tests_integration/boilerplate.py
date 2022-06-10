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
