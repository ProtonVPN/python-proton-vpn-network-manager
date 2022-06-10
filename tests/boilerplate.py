from dataclasses import dataclass
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
    netshield: int = None
    vpn_accelerator: bool = None
    port_forwarding: bool = None
    random_nat: bool = None
    safe_mode: bool = None


@dataclass
class Settings:
    dns_custom_ips: List[str] = None
    split_tunneling_ips: List[str] = None
    ipv6: bool = None
    features: Features = None
