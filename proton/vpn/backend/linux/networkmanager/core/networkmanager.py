import logging
from concurrent.futures import Future
from typing import Optional

from proton.loader import Loader
from proton.vpn.connection import VPNConnection, events, states
from proton.vpn.connection.vpnconfiguration import VPNConfiguration

from proton.vpn.backend.linux.networkmanager.core.nmclient import NM, NMClient, gi

logger = logging.getLogger(__name__)


class LinuxNetworkManager(VPNConnection):
    """Returns VPNConnections based on Linux Network Manager backend.

    This is the default backend that will be returned. See docstring for
    VPNConnection.get_vpnconnection() for further explanation on
    how priorities work.

    A LinuxNetworkManager can return a VPNConnection based on protocols
    such as OpenVPN, IKEv2 or Wireguard.
    """
    backend = "linuxnetworkmanager"

    def __init__(self, *args, nm_client: NMClient = None, **kwargs):
        self.__nm_client = nm_client
        super().__init__(*args, **kwargs)

    @property
    def nm_client(self):
        if not self.__nm_client:
            self.__nm_client = NMClient()

        return self.__nm_client

    @classmethod
    def factory(cls, protocol: str = None):
        """Returns the VPN connection implementation class
         for the specified protocol."""
        return Loader.get("nm_protocol", class_name=protocol)

    def start_connection(self):
        future = self._setup()  # Creates the network manager connection.
        future.add_done_callback(self._start_connection)

    def _start_connection(self, connection_setup_future: Future):
        # Calling result() will re-raise any exceptions raised during the connection setup.
        connection_setup_future.result()

        start_connection_future = self.nm_client.start_connection_async(
            self._get_nm_connection()
        )

        def hook_vpn_state_changed_callback(
                start_connection_future_done: Future
        ):
            vpn_connection = start_connection_future_done.result()
            vpn_connection.connect(
                "vpn-state-changed",
                self._on_vpn_state_changed
            )

        # start_connection_future is done as soon as the VPN connection
        # is activated, but before it's established. As soon as the
        # connection is activated, we start listening for vpn state changes.
        start_connection_future.add_done_callback(hook_vpn_state_changed_callback)

    def stop_connection(self, connection=None):
        connection = connection or self._get_nm_connection()
        self.nm_client.remove_connection_async(connection)

    def _on_vpn_state_changed(
            self, vpn_connection: NM.VpnConnection, state: int, reason: int
    ):
        """
            When the vpn state changes, NM emits a signal with the state and
            reason for the change. This callback will receive these updates
            and translate for them accordingly for the state machine,
            as the state machine is backend agnostic.

            :param state: connection state update
            :type state: int
            :param reason: the reason for the state update
            :type reason: int
        """
        try:
            state = NM.VpnConnectionState(state)
        except ValueError:
            logger.warning(f"Unexpected VPN connection state: {state}.")
            state = NM.VpnConnectionState.UNKNOWN

        try:
            reason = NM.VpnConnectionStateReason(reason)
        except ValueError:
            logger.warning(f"Unexpected VPN connection state reason: {reason}.")
            reason = NM.VpnConnectionStateReason.UNKNOWN

        logger.debug(
            f"VPN connection state changed: state={state.value_name}, "
            f"reason={reason.value_name}"
        )

        if state == NM.VpnConnectionState.ACTIVATED:
            self.on_event(events.Connected())
        elif state == NM.VpnConnectionState.FAILED:
            if reason in [
                NM.VpnConnectionStateReason.CONNECT_TIMEOUT,
                NM.VpnConnectionStateReason.SERVICE_START_TIMEOUT
            ]:
                self.on_event(events.Timeout(reason))
            elif reason in [
                NM.VpnConnectionStateReason.NO_SECRETS,
                NM.VpnConnectionStateReason.LOGIN_FAILED
            ]:
                self.on_event(events.AuthDenied(reason))
            elif reason in [
                NM.VpnConnectionStateReason.IP_CONFIG_INVALID,
                NM.VpnConnectionStateReason.SERVICE_STOPPED,
                NM.VpnConnectionStateReason.CONNECTION_REMOVED,
                NM.VpnConnectionStateReason.SERVICE_START_FAILED,
            ]:
                self.on_event(events.TunnelSetupFail(reason))
            elif reason in [
                NM.VpnConnectionStateReason.DEVICE_DISCONNECTED,
                NM.VpnConnectionStateReason.USER_DISCONNECTED
            ]:
                self.on_event(events.Disconnected(reason))
            else:  # reason UNKNOWN or NONE
                self.on_event(events.UnknownError(reason))
        elif state == NM.VpnConnectionState.DISCONNECTED:
            self.on_event(events.Disconnected(reason))
        else:
            logger.debug(f"Ignoring VPN state change: {state.value_name}.")

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
        self._ensure_unique_id_is_set()
        active_connection = self._get_nm_active_connection()
        if active_connection:
            self.update_connection_state(states.Connected())
            active_connection.connect(
                "vpn-state-changed",
                self._on_vpn_state_changed
            )
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

    def _import_vpn_config(
            self,
            vpnconfig: VPNConfiguration
    ) -> NM.SimpleConnection:
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
        connection.normalize()

        return connection

    def _get_nm_active_connection(self) -> Optional[NM.ActiveConnection]:
        """Gets ProtonVPN connection, if there is one and is active."""
        if not self._unique_id:
            return None
        return self.nm_client.get_active_connection(self._unique_id)

    def _get_nm_connection(self) -> Optional[NM.RemoteConnection]:
        """Get ProtonVPN connection, if there is one."""
        if not self._unique_id:
            return None
        return self.nm_client.get_connection(self._unique_id)
