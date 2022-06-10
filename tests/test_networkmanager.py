from concurrent.futures import Future
from unittest.mock import Mock, patch

import pytest
from proton.vpn.connection import events, states

from proton.vpn.backend.linux.networkmanager.core.enum import VPNConnectionStateEnum, VPNConnectionReasonEnum
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
                VPNConnectionStateEnum.IS_ACTIVE,
                VPNConnectionReasonEnum.NOT_PROVIDED,
                events.Connected
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.CONN_ATTEMPT_TO_SERVICE_TIMED_OUT,
                events.Timeout
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.TIMEOUT_WHILE_STARTING_VPN_SERVICE_PROVIDER,
                events.Timeout
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.SECRETS_WERE_NOT_PROVIDED,
                events.AuthDenied
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.SERVER_AUTH_FAILED,
                events.AuthDenied
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.IP_CONFIG_WAS_INVALID,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.SERVICE_PROVIDER_WAS_STOPPED,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.CREATE_SOFTWARE_DEVICE_LINK_FAILED,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.MASTER_CONN_FAILED_TO_ACTIVATE,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.DELETED_FROM_SETTINGS,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.START_SERVICE_VPN_CONN_SERVICE_FAILED,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.VPN_DEVICE_DISAPPEARED,
                events.TunnelSetupFail
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.DEVICE_WAS_DISCONNECTED,
                events.Disconnected
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.USER_HAS_DISCONNECTED,
                events.Disconnected
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.UNKNOWN,
                events.UnknownError
        ),
        (
                VPNConnectionStateEnum.FAILED,
                VPNConnectionReasonEnum.NOT_PROVIDED,
                events.UnknownError
        ),
        (
                VPNConnectionStateEnum.DISCONNECTED,
                VPNConnectionReasonEnum.NOT_PROVIDED,
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


