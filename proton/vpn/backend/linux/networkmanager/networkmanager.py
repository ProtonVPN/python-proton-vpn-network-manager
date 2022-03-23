from proton.vpn.backend.linux.networkmanager.enum import (
    VPNConnectionReasonEnum, VPNConnectionStateEnum)
from proton.vpn.connection import VPNConnection, event

from dbus.mainloop.glib import DBusGMainLoop

from .connection_monitor import ConnectionMonitor
from .nmclient import NM, GLib, NMClient, gi


class LinuxNetworkManager(VPNConnection, NMClient):
    """Returns VPNConnections based on Linux Network Manager backend.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A LinuxNetworkManager can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """

    backend = "linuxnetworkmanager"

    def __init__(self, *args, **kwargs):
        NMClient.__init__(self)
        VPNConnection.__init__(self, *args, **kwargs)

    @classmethod
    def factory(cls, protocol: str = None):
        """Get VPN connection.

        Returns vpn connection based on specified procotol from factory.
        """
        from proton.loader import Loader
        all_protocols = Loader.get_all("nm_protocol")

        if not all_protocols:
            return None

        for _p in all_protocols:
            if _p.class_name == protocol and _p.cls._validate():
                return _p.cls

    def _start_connection(self):
        import threading
        thread = threading.Thread(target=self._start_connection_in_thread)
        thread.start()

    def _start_connection_in_thread(self):
        self._setup()
        self._start_connection_async(self._get_nm_connection())

        # To catch signals from network manager, these are the necessary steps:
        # https://dbus.freedesktop.org/doc/dbus-python/tutorial.html#setting-up-an-event-loop
        DBusGMainLoop(set_as_default=True)
        self.__dbus_loop = GLib.MainLoop()
        ConnectionMonitor(
            self._unique_id,
            self._proxy_on_vpn_state_changed
        )
        self.__dbus_loop.run()

    def _proxy_on_vpn_state_changed(self, state, reason):
        state = VPNConnectionStateEnum(state)
        reason = VPNConnectionReasonEnum(reason)

        if state == VPNConnectionStateEnum.IS_ACTIVE:
            self.__dbus_loop.quit()
            self.on_event(event.Connected())
        elif state == VPNConnectionStateEnum.FAILED:
            if reason in [
                VPNConnectionReasonEnum.CONN_ATTEMPT_TO_SERVICE_TIMED_OUT,
                VPNConnectionReasonEnum.TIMEOUT_WHILE_STARTING_VPN_SERVICE_PROVIDER
            ]:
                self.__dbus_loop.quit()
                self.on_event(event.Timeout(reason))
            elif reason in [
                VPNConnectionReasonEnum.SECRETS_WERE_NOT_PROVIDED,
                VPNConnectionReasonEnum.SERVER_AUTH_FAILED
            ]:
                self.__dbus_loop.quit()
                self.on_event(event.AuthDenied(reason))
            elif reason in [
                VPNConnectionReasonEnum.IP_CONFIG_WAS_INVALID,
                VPNConnectionReasonEnum.SERVICE_PROVIDER_WAS_STOPPED,
                VPNConnectionReasonEnum.CREATE_SOFTWARE_DEVICE_LINK_FAILED,
                VPNConnectionReasonEnum.MASTER_CONN_FAILED_TO_ACTIVATE,
                VPNConnectionReasonEnum.DELETED_FROM_SETTINGS,
                VPNConnectionReasonEnum.START_SERVICE_VPN_CONN_SERVICE_FAILED,
                VPNConnectionReasonEnum.VPN_DEVICE_DISAPPEARED
            ]:
                self.__dbus_loop.quit()
                self.on_event(event.TunnelSetupFail(reason))
            elif reason in [
                VPNConnectionReasonEnum.DEVICE_WAS_DISCONNECTED,
                VPNConnectionReasonEnum.USER_HAS_DISCONNECTED
            ]:
                self.__dbus_loop.quit()
                self.on_event(event.Disconnected(reason))
            elif reason in [
                VPNConnectionReasonEnum.UNKNOWN,
                VPNConnectionReasonEnum.NOT_PROVIDED
            ]:
                self.__dbus_loop.quit()
                self.on_event(event.UnknownError(reason))

        elif state == VPNConnectionStateEnum.DISCONNECTED:
            print("Disconnected", state, reason)
            # FIX-ME: inform the state machine based on VPNConnectionReasonEnum reasons
            self.__dbus_loop.quit()

    def _determine_initial_state(self) -> "None":
        from proton.vpn.connection.state import (ConnectedState,
                                                 DisconnectedState)

        if self._get_nm_connection():
            self._update_connection_state(ConnectedState())
        else:
            self._update_connection_state(DisconnectedState())

    def _stop_connection(self):
        import threading
        thread = threading.Thread(target=self._stop_connection_in_thread)
        thread.start()

    def _stop_connection_in_thread(self):
        DBusGMainLoop(set_as_default=True)
        self.__dbus_loop = GLib.MainLoop()
        ConnectionMonitor(
            self._unique_id,
            self._act_on_if_has_connection_been_removed,
            True
        )
        self.__dbus_loop.run()

    def _act_on_if_has_connection_been_removed(self, has_connection_been_removed):
        self.__dbus_loop.quit()
        if has_connection_been_removed:
            self.on_event(event.Disconnected())
        else:
            self.on_event(event.UnknownError("Unable to disconnect"))

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

    @classmethod
    def _get_connection(cls):
        from proton.vpn.connection.state import ConnectedState
        from proton.loader import Loader
        all_protocols = Loader.get_all("nm_protocol")

        for _p in all_protocols:
            vpnconnection = _p.cls(None, None)
            if vpnconnection.status.state == ConnectedState.state:
                return vpnconnection

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

    def _get_nm_connection(self):
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
            # Since a connection can be removed at any point, an AttributeError try/catch
            # has to be performed, to ensure that a connection that existed previously
            # was not removed.
            try:
                if conn.get_connection_type() != "vpn" and conn.get_connection_type() != "wireguard":
                    continue

                try:
                    conn = conn.get_connection()
                except AttributeError:
                    pass

                if conn.get_uuid() == self._unique_id:
                    return conn
            except AttributeError:
                pass

        return None
