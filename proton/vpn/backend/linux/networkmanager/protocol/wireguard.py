from proton.vpn.backend.linux.networkmanager import LinuxNetworkManager

import gi
gi.require_version("NM", "1.0")
from gi.repository import NM


class Wireguard(LinuxNetworkManager):
    """Creates a Wireguard connection."""
    protocol = "wireguard"
    _persistence_prefix = "nm_{}_".format(protocol)
    virtual_device_name = "proton0"

    def __generate_unique_id(self):
        import uuid
        self._unique_id = str(uuid.uuid4())

    def __add_connection_to_nm(self):
        import dbus

        s_con = dbus.Dictionary({
            "type": "wireguard",
            "uuid": self._unique_id,
            "id": self._get_servername(),
            "interface-name": Wireguard.virtual_device_name
        })
        con = dbus.Dictionary({"connection": s_con})
        bus = dbus.SystemBus()
        proxy = bus.get_object(
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager/Settings"
        )
        settings = dbus.Interface(
            proxy,
            "org.freedesktop.NetworkManager.Settings"
        )
        settings.AddConnection(con)

    def __configure_connection(self):
        import socket

        # FIXME : Update connections cache, NMclient is a mess
        nm_client = NM.Client.new(None)
        connection = nm_client.get_connection_by_uuid(self._unique_id)
        s_wg = connection.get_setting(NM.SettingWireGuard)

        # https://lazka.github.io/pgi-docs/NM-1.0/classes/Connection.html#NM.Connection.get_setting
        ip4 = connection.get_setting_ip4_config()
        ip4.set_property('method', 'manual')
        s_wg.set_property(
            NM.SETTING_WIREGUARD_PRIVATE_KEY,
            self._vpncredentials.vpn_get_certificate_holder().vpn_client_private_wg_key
        )
        ip4.add_address(NM.IPAddress(socket.AF_INET, '10.2.0.2', 32))
        ip4.add_dns('10.2.0.1')
        ip4.add_dns_search('~')
        ipv6_config = connection.get_setting_ip6_config()
        ipv6_config.props.dns_priority = -1500
        ip4.props.dns_priority = -1500
        peer = NM.WireGuardPeer()
        peer.set_public_key(self._vpnserver.x25519pk, True)
        peer.set_endpoint(f'{self._vpnserver.server_ip}:{self._vpnserver.udp_ports[0]}', True)
        peer.append_allowed_ip('0.0.0.0/0', False)
        s_wg.append_peer(peer)
        connection.commit_changes(True, None)

    def __setup_wg_connection(self):
        self.__generate_unique_id()
        self.__add_connection_to_nm()
        self.__configure_connection()
        # FIXME : Update connections cache, NMclient is a mess
        nm_client = NM.Client.new(None)
        self.connection = nm_client.get_connection_by_uuid(self._unique_id)

        self.connection.commit_changes(True, None)
        self._commit_changes_async(self.connection)

    def _setup(self):
        self.__setup_wg_connection()
