import logging
from concurrent.futures import Future

from proton.vpn.backend.linux.networkmanager.core.enum import (
    VPNConnectionReasonEnum, VPNConnectionStateEnum)
from proton.vpn.connection import VPNConnection, events

from .nmclient import NM, GLib, NMClient, gi

logger = logging.getLogger(__name__)


class LinuxNetworkManager(VPNConnection):
    """Returns VPNConnections based on Linux Network Manager backend.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on how priorities work.

    A LinuxNetworkManager can return a VPNConnection based on protocols such as OpenVPN, IKEv2 or Wireguard.
    """
    backend = "linuxnetworkmanager"

    def __init__(self, *args, nm_client: NMClient = None, **kwargs):
        self._nm_client = nm_client
        super().__init__(*args, **kwargs)

    @property
    def nm_client(self):
        if not self._nm_client:
            self._nm_client = NMClient()

        return self._nm_client

    @classmethod
    def factory(cls, protocol: str = None):
        """Get VPN connection.

            Returns vpn connection based on specified procotol from factory.
        """
        from proton.vpn.connection.exceptions import MissingProtocolDetails
        from proton.loader import Loader

        all_protocols = Loader.get_all("nm_protocol")

        for _p in all_protocols:
            if _p.class_name == protocol and _p.cls._validate():
                return _p.cls

        raise MissingProtocolDetails("Could not find {} protocol".format(protocol))

    def start_connection(self, connection=None) -> Future:
        self._setup()  # Creates the network manager connection.
        connection = connection or self._get_nm_connection()
        start_connection_future = self.nm_client._start_connection_async(connection)

        def hook_vpn_state_changed_callback(start_connection_future_done: Future[NM.VpnConnection]):
            vpn_connection = start_connection_future_done.result()
            vpn_connection.connect("vpn-state-changed", self._on_vpn_state_changed)

        # start_connection_future is done as soon as the VPN connection is activated, but before it's established.
        # As soon as the connection is activated, we start listening for vpn state changes.
        start_connection_future.add_done_callback(hook_vpn_state_changed_callback)
        return start_connection_future

    def stop_connection(self, connection=None) -> Future:
        connection = connection or self._get_nm_connection()
        return self.nm_client._remove_connection_async(connection)

    def _on_vpn_state_changed(self, vpn_connection: NM.VpnConnection, state: int, reason: int):
        """
            When the vpn state changes, NM emits a signal with the state and reason
            for the change. This callback will receive these updates and translate for
            them accordingly for the state machine, as the state machine is backend agnostic.

            :param state: connection state update
            :type state: int
            :param reason: the reason for the state update
            :type reason: int
        """
        state = VPNConnectionStateEnum(state)
        reason = VPNConnectionReasonEnum(reason)

        if state == VPNConnectionStateEnum.IS_ACTIVE:
            self.on_event(events.Connected())
        elif state == VPNConnectionStateEnum.FAILED:
            if reason in [
                VPNConnectionReasonEnum.CONN_ATTEMPT_TO_SERVICE_TIMED_OUT,
                VPNConnectionReasonEnum.TIMEOUT_WHILE_STARTING_VPN_SERVICE_PROVIDER
            ]:
                self.on_event(events.Timeout(reason))
            elif reason in [
                VPNConnectionReasonEnum.SECRETS_WERE_NOT_PROVIDED,
                VPNConnectionReasonEnum.SERVER_AUTH_FAILED
            ]:
                self.on_event(events.AuthDenied(reason))
            elif reason in [
                VPNConnectionReasonEnum.IP_CONFIG_WAS_INVALID,
                VPNConnectionReasonEnum.SERVICE_PROVIDER_WAS_STOPPED,
                VPNConnectionReasonEnum.CREATE_SOFTWARE_DEVICE_LINK_FAILED,
                VPNConnectionReasonEnum.MASTER_CONN_FAILED_TO_ACTIVATE,
                VPNConnectionReasonEnum.DELETED_FROM_SETTINGS,
                VPNConnectionReasonEnum.START_SERVICE_VPN_CONN_SERVICE_FAILED,
                VPNConnectionReasonEnum.VPN_DEVICE_DISAPPEARED
            ]:
                self.on_event(events.TunnelSetupFail(reason))
            elif reason in [
                VPNConnectionReasonEnum.DEVICE_WAS_DISCONNECTED,
                VPNConnectionReasonEnum.USER_HAS_DISCONNECTED
            ]:
                self.on_event(events.Disconnected(reason))
            elif reason in [
                VPNConnectionReasonEnum.UNKNOWN,
                VPNConnectionReasonEnum.NOT_PROVIDED
            ]:
                self.on_event(events.UnknownError(reason))

        elif state == VPNConnectionStateEnum.DISCONNECTED:
            self.on_event(events.Disconnected(reason))

    @classmethod
    def _get_connection(cls):
        from proton.vpn.connection import states
        from proton.loader import Loader
        all_protocols = Loader.get_all("nm_protocol")

        for _p in all_protocols:
            vpnconnection = _p.cls(None, None)
            if vpnconnection.status.state == states.Connected.state:
                return vpnconnection

    def determine_initial_state(self) -> "None":
        """Determines the initial state of the state machine"""
        from proton.vpn.connection import states

        if self._get_nm_connection():
            self.update_connection_state(states.Connected())
        else:
            self.update_connection_state(states.Disconnected())

    def _get_servername(self) -> "str":
        servername = "ProtonVPN Connection"
        try:
            servername = "ProtonVPN {}".format(
                self._vpnserver.servername
                if self._vpnserver.servername
                else "Connection"
            )
        except AttributeError:
            servername = "ProtonVPN Connection"

        return servername

    def _setup(self):
        """
            Every protocol derived from this class has to override this method
            in order to have it working. Look at `_start_connection_in_thread`
            on how this is used.
        """
        raise NotImplementedError

    @classmethod
    def _get_priority(cls):
        return 100

    @classmethod
    def _validate(cls):
        # FIX ME: This should do a validation to ensure that NM can be used
        return True

    def _import_vpn_config(self, vpnconfig: "proton.vpn.connection.vpnconfiguration.VPNConfiguration") -> "NM.SimpleConnection":
        """
            Imports the vpn connection configurations into NM
            and stores the connection on non-volatile memory.

            :return: imported vpn connection
            :rtype: NM.SimpleConnection
        """
        plugin_info = NM.VpnPluginInfo
        vpn_plugin_list = plugin_info.list_load()

        connection = None
        with vpnconfig as filename:
            for plugin in vpn_plugin_list:
                plugin_editor = plugin.load_editor_plugin()
                # return a NM.SimpleConnection (NM.Connection)
                # https://lazka.github.io/pgi-docs/NM-1.0/classes/SimpleConnection.html
                try:
                    # plugin_name = plugin.props.name
                    connection = plugin_editor.import_(filename)
                    break
                except gi.repository.GLib.Error:
                    continue

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

        :return: vpn connection
        :rtype: NM.RemoteConnection
        """
        self._ensure_unique_id_is_set()
        if not self._unique_id:
            return None

        # Gets all active connections
        active_conn_list = self.nm_client.nm_client.get_active_connections()
        # Gets all non-active stored connections
        non_active_conn_list = self.nm_client.nm_client.get_connections()

        # The reason for having this difference is because NM can
        # have active connections that are not stored. If such
        # connection is stopped/disabled then it is removed from
        # NM, and thus the distinction between active and "regular" connections.

        all_conn_list = active_conn_list + non_active_conn_list

        for conn in all_conn_list:
            # Since a connection can be removed at any point, an AttributeError try/catch
            # has to be performed, to ensure that a connection that existed previously when
            # doing the `if` statement was not removed.
            try:
                if (
                    conn.get_connection_type().lower() != "vpn"
                    and conn.get_connection_type().lower() != "wireguard"
                ):
                    continue

                # If it's an active connection then we attempt to get
                # its stored connection. If an AttributeError is raised
                # then it means that the conneciton is a stored connection
                # and not an active connection, and thus the exception
                # can be safely ignored.
                try:
                    conn = conn.get_connection()
                except AttributeError:
                    pass

                if self._unique_id == conn.get_uuid():
                    return conn
            except AttributeError:
                pass

        return None

    def release_resources(self):
        # TODO add this method to VPNConnection so that implementations get the chance to clean resources
        # VPNConnection.release_resources(self)
        self.nm_client.release_resources()
