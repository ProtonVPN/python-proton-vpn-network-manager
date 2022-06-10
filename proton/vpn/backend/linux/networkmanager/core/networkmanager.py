import logging
from concurrent.futures import Future

from proton.loader import Loader

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
        """Returns the VPN connection implementation class for the specified protocol."""
        return Loader.get("nm_protocol", class_name=protocol)

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
        servername = self._vpnserver.servername or "Connection"
        return f"ProtonVPN {servername}"

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
        vpn_plugin_list = NM.VpnPluginInfo.list_load()

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
            # FIXME: Why do we have this pass statement here?
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

        return self.nm_client.get_connection(self._unique_id)

    def release_resources(self):
        # TODO add this method to VPNConnection so that implementations get the chance to clean resources
        # VPNConnection.release_resources(self)
        self.nm_client.release_resources()
