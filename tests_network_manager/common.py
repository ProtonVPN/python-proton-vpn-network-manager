from proton.vpn.connection.interfaces import (Settings, VPNCredentials,
                                              VPNPubkeyCredentials, VPNServer,
                                              VPNUserPassCredentials)
import pathlib
import os

CWD = str(pathlib.Path(__file__).parent.absolute())
PERSISTANCE_CWD = os.path.join(
    CWD,
    "connection_persistence"
)


class MalformedVPNCredentials:
    pass


class MalformedVPNServer:
    pass


class MockVpnServer(VPNServer):
    @property
    def server_ip(self):
        return "10.10.1.1"

    @property
    def domain(self):
        return "com.test-domain.www"

    @property
    def wg_public_key_x25519(self):
        return "wg_public_key"

    @property
    def tcp_ports(self):
        return [445, 5995]

    @property
    def udp_ports(self):
        return [80, 1194]

    @property
    def servername(self):
        return "TestServer#10"


class MockVPNPubkeyCredentials(VPNPubkeyCredentials):
    @property
    def certificate_pem(self):
        return "pem-cert"

    @property
    def wg_private_key(self):
        return "wg-private-key"

    @property
    def openvpn_private_key(self):
        return "ovpn-private-key"


class MockVPNUserPassCredentials(VPNUserPassCredentials):
    @property
    def username(self):
        return "test-username"

    @property
    def password(self):
        return "test-password"


class MockVpnCredentials(VPNCredentials):
    @property
    def pubkey_credentials(self):
        return MockVPNPubkeyCredentials()

    @property
    def userpass_credentials(self):
        return MockVPNUserPassCredentials()


class MockSettings(Settings):
    @property
    def dns_custom_ips(self):
        return ["1.1.1.1", "10.10.10.10"]

    @property
    def split_tunneling_ips(self):
        return ["192.168.1.102", "192.168.5.99", "192.168.1.12/16"]

    @property
    def ipv6(self):
        return False
