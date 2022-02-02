import gi
from proton.vpn.connection import VPNConnection

gi.require_version("NM", "1.0")

from gi.repository import NM
from .nmclient import NMClient


class LinuxNetworkManager(VPNConnection, NMClient):
    """Returns VPNConnections based on Linux Network Manager backend.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A LinuxNetworkManager can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """

    backend = "linuxnetworkmanager"

    @classmethod
    def factory(cls, protocol: str = None):
        """Get VPN connection.

        Returns vpn connection based on specified procotol from factory.
        """
        if "openvpn" in protocol.lower():
            from proton.vpn.backend.linux.networkmanager.protocol import OpenVPN
            return OpenVPN.get_by_protocol(protocol)
        elif "wireguard" in protocol.lower():
            from proton.vpn.backend.linux.networkmanager.protocol import Wireguard
            return Wireguard
        elif "ikev2" in protocol.lower():
            from proton.vpn.backend.linux.networkmanager.protocol import Strongswan
            return Strongswan

    def up(self):
        self._setup()
        self._persist_connection()
        self._start_connection_async(self._get_protonvpn_connection())

    def down(self):
        self._remove_connection_async(self._get_protonvpn_connection())
        self._remove_connection_persistence()

    @classmethod
    def _get_connection(cls):
        from proton.vpn.backend.linux.networkmanager.protocol import (Strongswan,
                                                            Wireguard)
        from proton.vpn.backend.linux.networkmanager.protocol.openvpn import (OpenVPNTCP,
                                                                    OpenVPNUDP)

        classes = [OpenVPNTCP, OpenVPNUDP, Wireguard, Strongswan]

        for _class in classes:
            vpnconnection = _class(None, None)
            if vpnconnection._get_protonvpn_connection():
                return vpnconnection

    def _get_servername(self) -> str:
        servername = "ProtonVPN Connection"
        try:
            servername = "ProtonVPN {}".format(
                self._vpnserver.servername
                if self._vpnserver.servername
                else "Connection"
            )
        except AttributeError:
            pass

        return servername

    def _setup(self):
        raise NotImplementedError

    @classmethod
    def _get_priority(cls):
        return 100

    @classmethod
    def _validate(cls):
        # FIX ME: This should do a validation to ensure that NM can be used
        return True

    def _import_vpn_config(self, vpnconfig):
        plugin_info = NM.VpnPluginInfo
        vpn_plugin_list = plugin_info.list_load()

        with vpnconfig as filename:
            for plugin in vpn_plugin_list:
                plugin_editor = plugin.load_editor_plugin()
                # return a NM.SimpleConnection (NM.Connection)
                # https://lazka.github.io/pgi-docs/NM-1.0/classes/SimpleConnection.html
                try:
                    connection = plugin_editor.import_(filename)
                    # plugin_name = plugin.props.name
                except gi.repository.GLib.Error:
                    pass

        if connection is None:
            raise NotImplementedError(
                "Support for given configuration is not implemented"
            )

        # https://lazka.github.io/pgi-docs/NM-1.0/classes/Connection.html#NM.Connection.normalize
        if connection.normalize():
            pass

        return connection

    def _get_protonvpn_connection(self, from_active=False):
        """Get ProtonVPN connection.

        Returns:
            if:
            - NetworkManagerConnectionTypeEnum.ALL: NM.RemoteConnection
            - NetworkManagerConnectionTypeEnum.ACTIVE: NM.ActiveConnection
        """

        active_conn_list = self.nm_client.get_active_connections()
        non_active_conn_list = self.nm_client.get_connections()

        all_conn_list = active_conn_list + non_active_conn_list

        self._ensure_unique_id_is_set()
        if not self._unique_id:
            return None

        for conn in all_conn_list:
            if conn.get_connection_type() != "vpn" and conn.get_connection_type() != "wireguard":
                continue

            try:
                conn = conn.get_connection()
            except AttributeError:
                pass

            if conn.get_uuid() == self._unique_id:
                return conn

        return None
