from concurrent.futures import Future
from unittest.mock import Mock, patch

import gi
gi.require_version("NM", "1.0")  # noqa: required before importing NM module
from gi.repository import NM, GLib

import pytest

from tests.boilerplate import VPNServer, VPNCredentials, Settings
from proton.vpn.backend.linux.networkmanager.core import LinuxNetworkManager
from proton.vpn.connection import states
from proton.vpn.connection import events


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


def test_start_connection(nm_protocol, nm_client_mock):
    # mock setup connection
    setup_connection_future = Future()
    nm_protocol._setup.return_value = setup_connection_future

    start_connection_future = Future()
    nm_client_mock.start_connection_async.return_value = start_connection_future

    nm_protocol.start_connection()

    nm_protocol._setup.assert_called_once()

    # Simulate setup connection finished.
    connection_mock = Mock()
    setup_connection_future.set_result(connection_mock)

    nm_client_mock.start_connection_async.assert_called_once_with(connection_mock)

    # Assert that once the connection has been activated, the expected callback
    # is hooked to monitor vpn connection state changes.
    start_connection_future.set_result(connection_mock)
    connection_mock.connect.assert_called_once_with("vpn-state-changed", nm_protocol._on_vpn_state_changed)


def test_start_connection_generates_tunnel_setup_failed_event_on_connection_setup_errors(
        nm_protocol, nm_client_mock
):
    # Mock error on connection setup.
    setup_connection_future = Future()
    setup_connection_future.set_exception(GLib.GError)
    nm_protocol._setup.return_value = setup_connection_future

    with patch.object(nm_protocol, "on_event"):
        nm_protocol.start_connection()

        nm_protocol._setup.assert_called()
        nm_protocol.on_event.assert_called_once()

        generated_event = nm_protocol.on_event.call_args[0][0]
        assert isinstance(generated_event, events.TunnelSetupFailed)


def test_start_connection_generates_tunnel_setup_failed_event_on_connection_activation_errors_and_removes_connection(
        nm_protocol, nm_client_mock
):
    # Mock successful connection setup.
    connection = Mock()
    setup_connection_future = Future()
    setup_connection_future.set_result(connection)
    nm_protocol._setup.return_value = setup_connection_future

    # Mock error on connection activation.
    start_connection_future = Future()
    start_connection_future.set_exception(GLib.GError)
    nm_client_mock.start_connection_async.return_value = start_connection_future

    with patch.object(nm_protocol, "on_event"), patch.object(nm_protocol, "remove_connection"):
        nm_protocol.start_connection()

        nm_client_mock.start_connection_async.assert_called_once_with(connection)
        nm_protocol.on_event.assert_called_once()

        generated_event = nm_protocol.on_event.call_args[0][0]
        assert isinstance(generated_event, events.TunnelSetupFailed)

        nm_protocol.remove_connection.assert_called_once()


def test_stop_connection(nm_protocol, nm_client_mock):
    connection_mock = Mock()
    nm_protocol.stop_connection(connection_mock)
    nm_client_mock.stop_connection_async.assert_called_once_with(connection_mock)


def test_remove_connection(nm_protocol, nm_client_mock):
    connection_mock = Mock()
    nm_protocol.remove_connection(connection_mock)
    nm_client_mock.remove_connection_async.assert_called_once_with(connection_mock)
    assert nm_protocol._unique_id is None


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
                events.UnexpectedError
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.SERVICE_STOPPED,
                events.UnexpectedError
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.CONNECTION_REMOVED,
                events.UnexpectedError
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.SERVICE_START_FAILED,
                events.UnexpectedError
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.UNKNOWN,
                events.UnexpectedError
        ),
        (
                NM.VpnConnectionState.FAILED,
                NM.VpnConnectionStateReason.NONE,
                events.UnexpectedError
        ),
        (
                NM.VpnConnectionState.DISCONNECTED,
                NM.VpnConnectionStateReason.DEVICE_DISCONNECTED,
                events.DeviceDisconnected
        ),
        (
                NM.VpnConnectionState.DISCONNECTED,
                NM.VpnConnectionStateReason.USER_DISCONNECTED,
                events.Disconnected
        ),
        (
                NM.VpnConnectionState.DISCONNECTED,
                NM.VpnConnectionStateReason.NONE,
                events.UnexpectedError
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
@patch("proton.vpn.backend.linux.networkmanager.core.networkmanager.LinuxNetworkManager._get_nm_active_connection")
@patch("proton.vpn.backend.linux.networkmanager.core.networkmanager.LinuxNetworkManager._ensure_unique_id_is_set")
def test_determine_initial_state(
        _ensure_unique_id_is_set_mock, _get_nm_active_connection_mock,
        update_connection_state_mock, nm_protocol, nm_connection, expected_state
):
    _get_nm_active_connection_mock.return_value = nm_connection

    nm_protocol.determine_initial_state()

    _ensure_unique_id_is_set_mock.assert_called_once_with()
    update_connection_state_mock.assert_called_once()
    assert isinstance(update_connection_state_mock.call_args.args[0], expected_state)


