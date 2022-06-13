from concurrent.futures import Future
from unittest.mock import Mock, patch

import gi
gi.require_version("NM", "1.0")  # noqa: required before importing NM module
from gi.repository import NM

import pytest

from proton.vpn.connection import events, states

from tests.boilerplate import VPNServer, VPNCredentials, Settings
from proton.vpn.backend.linux.networkmanager.core import LinuxNetworkManager


class LinuxNetworkManagerProtocol(LinuxNetworkManager):
    """Dummy protocol just to unit test the base LinuxNetworkManager class."""
    protocol = "Dummy protocol"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The _setup method is mocked. This method should be the one setting up
        # the NetworkManager connection. Protocols, inheriting from LinuxNetworkManager
        # are expected to implement it.
        self._setup = Mock()


@pytest.fixture
def nm_client_mock():
    return Mock()


@pytest.fixture
def nm_protocol(nm_client_mock):
    return LinuxNetworkManagerProtocol(
        VPNServer(), VPNCredentials(), Settings(), nm_client=nm_client_mock
    )


@patch("proton.vpn.backend.linux.networkmanager.core.networkmanager.LinuxNetworkManager._get_nm_connection")
def test_start_connection(_get_nm_connection_mock, nm_protocol, nm_client_mock):
    # mock NM connection
    connection_mock = Mock()
    _get_nm_connection_mock.return_value = connection_mock

    start_connection_future = Future()
    nm_client_mock._start_connection_async.return_value = start_connection_future

    nm_protocol.start_connection()

    nm_protocol._setup.assert_called_once()
    nm_client_mock._start_connection_async.assert_called_once_with(connection_mock)
    # assert that once the connection has been activated, the expected callback is hooked
    # to monitor vpn connection state changes
    start_connection_future.set_result(connection_mock)
    connection_mock.connect.assert_called_once_with("vpn-state-changed", nm_protocol._on_vpn_state_changed)


@patch("proton.vpn.backend.linux.networkmanager.core.networkmanager.LinuxNetworkManager._get_nm_connection")
def test_stop_connection(_get_nm_connection_mock, nm_protocol, nm_client_mock):
    # mock NM connection
    connection_mock = Mock()
    _get_nm_connection_mock.return_value = connection_mock

    nm_protocol.stop_connection(connection_mock)

    nm_client_mock._remove_connection_async.assert_called_once_with(connection_mock)


@pytest.mark.parametrize(
    "state, reason, expected_event",
    [
        (
                NM.VpnConnectionState.ACTIVATED,
                NM.VpnConnectionStateReason.NONE,
                events.Connected
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.CONNECT_TIMEOUT,
                events.Timeout
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.SERVICE_START_TIMEOUT,
                events.Timeout
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.NO_SECRETS,
                events.AuthDenied
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.LOGIN_FAILED,
                events.AuthDenied
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.IP_CONFIG_INVALID,
                events.TunnelSetupFail
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.SERVICE_STOPPED,
                events.TunnelSetupFail
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.CONNECTION_REMOVED,
                events.TunnelSetupFail
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.SERVICE_START_FAILED,
                events.TunnelSetupFail
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.DEVICE_DISCONNECTED,
                events.Disconnected
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.USER_DISCONNECTED,
                events.Disconnected
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.UNKNOWN,
                events.UnknownError
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.NONE,
                events.UnknownError
        ),
        (
                NM.VpnConnectionState.DISCONNECTED,
                NM.VpnConnectionStateReason.NONE,
                events.Disconnected
        ),
    ]
)
@patch("proton.vpn.backend.linux.networkmanager.core.LinuxNetworkManager.on_event")
def test_on_vpn_state_changed(on_event, nm_protocol, state, reason, expected_event):
    nm_protocol._on_vpn_state_changed(None, state, reason)

    # assert that the LinuxNetworkManager.on_event method was called with the expected event
    on_event.assert_called_once()
    assert isinstance(on_event.call_args.args[0], expected_event)


@pytest.mark.parametrize(
    "nm_connection, expected_state",
    [
        (
                Mock(),
                states.Connected,  # When there is an existing connection the initial state is connected.
        ),
        (
                None,
                states.Disconnected  # When there is not a connection, the initial state is disconnected.
        ),
    ]
)
@patch("proton.vpn.backend.linux.networkmanager.core.networkmanager.LinuxNetworkManager.update_connection_state")
@patch("proton.vpn.backend.linux.networkmanager.core.networkmanager.LinuxNetworkManager._get_nm_connection")
def test_determine_initial_state(_get_nm_connection_mock, update_connection_state_mock, nm_protocol, nm_connection, expected_state):
    _get_nm_connection_mock.return_value = nm_connection

    nm_protocol.determine_initial_state()

    update_connection_state_mock.assert_called_once()
    assert isinstance(update_connection_state_mock.call_args.args[0], expected_state)


