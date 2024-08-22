"""
This module contains the backends implementing the supported OpenVPN protocols.


Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncio
import socket
import uuid
import logging
from getpass import getuser
from concurrent.futures import Future

import gi

gi.require_version("NM", "1.0")  # noqa: required before importing NM module
# pylint: disable=wrong-import-position
from gi.repository import NM

from proton.vpn.connection import events, states
from proton.vpn.connection.events import EventContext
from proton.vpn.connection.interfaces import Settings, Features
from proton.vpn.backend.linux.networkmanager.core import LinuxNetworkManager
from proton.vpn.backend.linux.networkmanager.protocol.wireguard.local_agent \
    import Status, State, ReasonCode, AgentFeatures
from proton.vpn.backend.linux.networkmanager.protocol.wireguard.local_agent.listener \
    import AgentListener

logger = logging.getLogger(__name__)


class Wireguard(LinuxNetworkManager):
    """Creates a Wireguard connection."""
    SIGNAL_NAME = "state-changed"
    ADDRESS = "10.2.0.2"
    ADDRESS_PREFIX = 32
    DNS_IP = "10.2.0.1"
    DNS_SEARCH = "~"
    ALLOWED_IP = "0.0.0.0/0"
    DNS_PRIORITY = -1500
    VIRTUAL_DEVICE_NAME = "proton0"
    protocol = "wireguard"
    ui_protocol = "WireGuard (experimental)"
    connection = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connection_settings = None
        self._agent_listener = AgentListener(
            subscribers=[self._on_local_agent_status]
        )

    def setup(self) -> Future:
        """Methods that creates and applies any necessary changes to the connection."""
        self._generate_connection()
        self._modify_connection()
        return self.nm_client.add_connection_async(self.connection)

    def _generate_connection(self):
        self._unique_id = str(uuid.uuid4())
        self._connection_settings = NM.SettingConnection.new()
        self.connection = NM.SimpleConnection.new()

    async def update_credentials(self, credentials):
        """Notifies the vpn server that the wireguard certificate needs a refresh."""
        await super().update_credentials(credentials)
        await self._start_local_agent_listener()

    @property
    def are_feature_updates_applied_when_active(self) -> bool:
        """
        Returns whether the connection features updates are applied on the fly
        while the connection is already active, without restarting the connection.
        """
        return True

    async def update_settings(self, settings: Settings):
        """Update features on the active agent connection."""
        await super().update_settings(settings)
        if self._agent_listener.is_running:
            await self._request_connection_features(settings.features)

    def _modify_connection(self):
        self._set_custom_connection_id()
        self._set_uuid()
        self._set_interface_name()
        self._set_connection_type()
        self._set_connection_user_owned()
        self.connection.add_setting(self._connection_settings)

        self._set_route()
        self._set_dns()
        self._set_wireguard_properties()

        self.connection.verify()

    def _set_custom_connection_id(self):
        self._connection_settings.set_property(NM.SETTING_CONNECTION_ID, self._get_servername())

    def _set_uuid(self):
        self._connection_settings.set_property(NM.SETTING_CONNECTION_UUID, self._unique_id)

    def _set_interface_name(self):
        self._connection_settings.set_property(
            NM.SETTING_CONNECTION_INTERFACE_NAME, self.VIRTUAL_DEVICE_NAME
        )

    def _set_connection_type(self):
        self._connection_settings.set_property(NM.SETTING_CONNECTION_TYPE, "wireguard")

    def _set_connection_user_owned(self):
        self._connection_settings.add_permission(
            "user",
            getuser(),
            None
        )

    def _set_route(self):
        ipv4_config = NM.SettingIP4Config.new()
        ipv6_config = NM.SettingIP6Config.new()

        ipv4_config.set_property(NM.SETTING_IP_CONFIG_METHOD, "manual")
        ipv4_config.add_address(
            NM.IPAddress.new(socket.AF_INET, self.ADDRESS, self.ADDRESS_PREFIX)
        )

        ipv6_config.set_property(NM.SETTING_IP_CONFIG_METHOD, "disabled")

        self.connection.add_setting(ipv4_config)
        self.connection.add_setting(ipv6_config)

    def _set_dns(self):
        ipv4_config = self.connection.get_setting_ip4_config()
        ipv6_config = self.connection.get_setting_ip6_config()

        ipv4_config.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, self.DNS_PRIORITY)
        ipv6_config.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, self.DNS_PRIORITY)

        ipv4_config.set_property(NM.SETTING_IP_CONFIG_IGNORE_AUTO_DNS, True)
        ipv6_config.set_property(NM.SETTING_IP_CONFIG_IGNORE_AUTO_DNS, True)

        if self._settings.dns_custom_ips:
            ipv4_config.set_property(NM.SETTING_IP_CONFIG_DNS, self._settings.dns_custom_ips)
        else:
            ipv4_config.add_dns(self.DNS_IP)
            ipv4_config.add_dns_search(self.DNS_SEARCH)

        self.connection.add_setting(ipv4_config)
        self.connection.add_setting(ipv6_config)

    def _set_wireguard_properties(self):
        peer = NM.WireGuardPeer.new()
        peer.append_allowed_ip(self.ALLOWED_IP, False)
        peer.set_endpoint(
            f"{self._vpnserver.server_ip}:{self._vpnserver.wireguard_ports.udp[0]}",
            False
        )
        peer.set_public_key(self._vpnserver.x25519pk, False)

        # Ensures that the configurations are valid
        # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/WireGuardPeer.html#NM.WireGuardPeer.is_valid
        peer.is_valid(True, True)

        wireguard_config = NM.SettingWireGuard.new()
        wireguard_config.append_peer(peer)
        wireguard_config.set_property(
            NM.SETTING_WIREGUARD_PRIVATE_KEY,
            self._vpncredentials.pubkey_credentials.wg_private_key
        )

        self.connection.add_setting(wireguard_config)

    def _get_agent_features(self, features: Features) -> AgentFeatures:
        if features is None:
            # The free tier does not pass connection features since
            # our servers do not allow setting connection features on the free
            # tier, not even the defaults.
            return None

        return AgentFeatures(
            netshield_level=features.netshield,
            randomized_nat=not features.moderate_nat if features.moderate_nat is not None else None,
            split_tcp=features.vpn_accelerator,
            port_forwarding=features.port_forwarding,
            bouncing=self._vpnserver.label,
            jail=None  # Currently not in use
        )

    async def _start_local_agent_listener(self):
        if self._agent_listener.is_running:
            logger.info("Closing existing agent connection...")
            self._agent_listener.stop()

        logger.info("Waiting for agent status from %s...", self._vpnserver.domain)
        self._agent_listener.start(
            self._vpnserver.domain,
            self._vpncredentials.pubkey_credentials,
            self._get_agent_features(self._settings.features)
        )

    async def _on_local_agent_status(self, status: Status):
        """The local agent listener calls this method whenever a new status is
        read from the local agent connection."""
        logger.info("Agent status received: %s", status)
        if status.state == State.CONNECTED:
            self._notify_subscribers(events.Connected(EventContext(connection=self)))
        elif status.state == State.HARD_JAILED:
            self._handle_hard_jailed_state(status)
        elif status.state == State.DISCONNECTED:
            if status.reason and status.reason.code == ReasonCode.CERTIFICATE_EXPIRED:
                self._notify_subscribers(
                    events.ExpiredCertificate(EventContext(connection=self))
                )
            else:
                self._notify_subscribers(
                    events.Timeout(EventContext(connection=self))
                )
        else:
            self._notify_subscribers(
                events.UnexpectedError(EventContext(connection=self))
            )

    def _handle_hard_jailed_state(self, status: Status):
        if status.reason.code == ReasonCode.CERTIFICATE_EXPIRED:
            self._notify_subscribers(
                events.ExpiredCertificate(EventContext(connection=self))
            )
        elif self._has_reached_max_amount_of_concurrent_vpn_connections(status.reason.code):
            self._notify_subscribers(
                events.MaximumSessionsReached(EventContext(connection=self))
            )
        else:
            self._notify_subscribers(
                events.UnexpectedError(EventContext(connection=self))
            )

    def _has_reached_max_amount_of_concurrent_vpn_connections(self, code: ReasonCode) -> bool:
        """Check if a user has reached the maximum number of concurrent VPN sessions/connections
        permitted for the current tier."""
        return code in (
            ReasonCode.MAX_SESSIONS_UNKNOWN,
            ReasonCode.MAX_SESSIONS_FREE,
            ReasonCode.MAX_SESSIONS_BASIC,
            ReasonCode.MAX_SESSIONS_PLUS,
            ReasonCode.MAX_SESSIONS_VISIONARY,
            ReasonCode.MAX_SESSIONS_PRO
        )

    def _async_start_local_agent_listener(self):
        """This schedules a local agent listener in asyncio."""
        future = asyncio.run_coroutine_threadsafe(
            self._start_local_agent_listener(),
            self._asyncio_loop
        )
        future.add_done_callback(lambda f: f.result())

    async def _request_connection_features(self, features: Features):
        agent_features = self._get_agent_features(features)
        logger.info("Requesting VPN connection features...")
        await self._agent_listener.request_features(agent_features)
        logger.info("VPN connection features requested.")

    # pylint: disable=arguments-renamed
    def _on_state_changed(
            self, _: NM.ActiveConnection, state: int, reason: int
    ):
        """
            When the connection state changes, NM emits a signal with the state and
            reason for the change. This callback will receive these updates
            and translate for them accordingly for the state machine,
            as the state machine is backend agnostic.

            :param state: connection state update
            :type state: int
            :param reason: the reason for the state update
            :type reason: int
        """
        state = NM.ActiveConnectionState(state)
        reason = NM.ActiveConnectionStateReason(reason)

        logger.debug(
            "Wireguard connection state changed: state=%s, reason=%s",
            state.value_name, reason.value_name
        )

        if state is NM.ActiveConnectionState.ACTIVATED:
            self._async_start_local_agent_listener()
        elif state == NM.ActiveConnectionState.DEACTIVATED:
            self._agent_listener.stop()
            self._notify_subscribers_threadsafe(
                events.Disconnected(EventContext(connection=self, error=reason))
            )
        else:
            logger.debug("Ignoring VPN state change: %s", state.value_name)

    def _initialize_persisted_connection(
            self, connection_id: str
    ) -> states.State:
        """Implemented in wireguard so we can start local agent listener."""
        state = super()._initialize_persisted_connection(connection_id)

        if isinstance(state, states.Connected):
            self._async_start_local_agent_listener()
        return state

    @classmethod
    def _get_priority(cls):
        return 1

    @classmethod
    def _validate(cls):
        # FIX ME: This should do a validation to ensure that NM can be used
        return True
