from proton.vpn.backend.linux.networkmanager import LinuxNetworkManager
import os
from proton.utils import ExecutionEnvironment

import gi
gi.require_version("NM", "1.0")
from gi.repository import NM


class StrongswanProperties:
    # FIXME : Plugin seems to handle private key from a file, not really safe ?
    # FIXME : see if the plugin can accept anything else than files.
    CA_FILENAME = "protonvpnca.pem"
    PRIVATE_KEY_FILENAME = "key.pem"
    CERT_FILENAME = "cert.pem"


class Strongswan(LinuxNetworkManager):
    """Creates a Strongswan/IKEv2 connection."""
    protocol = "ikev2"
    _persistence_prefix = "nm_{}_".format(protocol)
    virtual_device_name = "proton0"

    PEM_CA_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,StrongswanProperties.CA_FILENAME)
    PRIVKEY_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,StrongswanProperties.PRIVATE_KEY_FILENAME)
    CERT_FILEPATH = os.path.join(ExecutionEnvironment().path_runtime,StrongswanProperties.CERT_FILENAME)

    def __generate_unique_id(self):
        import uuid
        self._unique_id = str(uuid.uuid4())

    def __configure_connection(self):
        from .constants import ca_cert
        new_connection = NM.SimpleConnection.new()

        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, self._get_servername())
        s_con.set_property(NM.SETTING_CONNECTION_UUID, self._unique_id)
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, "vpn")

        s_vpn = NM.SettingVpn.new()
        s_vpn.set_property(NM.SETTING_VPN_SERVICE_TYPE, "org.freedesktop.NetworkManager.strongswan")
        s_vpn.add_data_item("address", self._vpnserver.domain)
        s_vpn.add_data_item("encap", "no")
        s_vpn.add_data_item("ike", "aes256gcm16-ecp384")
        s_vpn.add_data_item("ipcomp", "no")
        s_vpn.add_data_item("password-flags", "1")
        s_vpn.add_data_item("proposal", "no")
        s_vpn.add_data_item("virtual", "yes")

        with open(Strongswan.PEM_CA_FILEPATH, "w") as f:
            f.write(ca_cert)
        s_vpn.add_data_item("certificate", Strongswan.PEM_CA_FILEPATH)

        if self._use_certificate:
            s_vpn.add_data_item("method", "key")
            api_cert = self._vpncredentials.vpn_get_certificate_holder().vpn_client_api_pem_certificate
            with open(Strongswan.CERT_FILEPATH, "w") as f:
                f.write(api_cert)
            # openvpn key should work.
            priv_key = self._vpncredentials.vpn_get_certificate_holder().vpn_client_private_openvpn_key
            with open(Strongswan.PRIVKEY_FILEPATH, "w") as f:
                f.write(priv_key)
            s_vpn.add_data_item("usercert", Strongswan.CERT_FILEPATH)
            s_vpn.add_data_item("userkey", Strongswan.PRIVKEY_FILEPATH)
        else:
            pass_creds = self._vpncredentials.vpn_get_username_and_password()
            s_vpn.add_data_item("method", "eap")
            s_vpn.add_data_item("user", pass_creds.username)
            s_vpn.add_secret("password", pass_creds.password)

        new_connection.add_setting(s_con)
        new_connection.add_setting(s_vpn)

        self.connection = new_connection

    def __add_dns(self):
        # FIXME : Update connections cache, NMclient is a mess
        nm_client = NM.Client.new(None)
        connection = nm_client.get_connection_by_uuid(self._unique_id)
        ip4_s = connection.get_setting_ip4_config()
        ip4_s.add_dns('10.2.0.1')
        ip4_s.add_dns_search('~.')
        ip4_s.props.dns_priority = -1500
        ipv6_config = connection.get_setting_ip6_config()
        ipv6_config.add_dns_search('~.')
        ipv6_config.props.dns_priority = -1500
        connection.commit_changes(True, None)

    def _setup(self):
        self.__generate_unique_id()
        self.__configure_connection()
        self._add_connection_async(self.connection)
        self.__add_dns()
