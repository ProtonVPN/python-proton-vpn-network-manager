from .common import MockVpnCredentials, MockVpnServer
from proton.vpn.backend.linux.networkmanager.enum import VPNConnectionReasonEnum, VPNConnectionStateEnum
from proton.vpn.connection import events, states
import pytest
import time

TIMEOUT_LIMIT = 5

# <<<<<<<<<<<<<
# <<<<<<<<<<<<< Needed mocks classes for testing
# <<<<<<<<<<<<<


class classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class MockStatusConnected:

    @classproperty
    def state(cls):
        return states.Connected().state


class MockStatusDisconnected:

    @classproperty
    def state(cls):
        return states.Disconnected().state


class MockBaseProtocol:
    protocol = None

    def __init__(self, *args):
        pass

    @classproperty
    def class_name(cls):
        return cls.protocol

    @classmethod
    def _validate(cls):
        return 100

    @classproperty
    def cls(cls, *args):
        return cls


class MockProtocolOne(MockBaseProtocol):
    protocol = "protocol-one"

    @property
    def status(self):
        return MockStatusConnected()


class MockProtocolTwo(MockBaseProtocol):
    protocol = "protocol-two"

    @property
    def status(self):
        return MockStatusDisconnected()


def modified_get_all(self, *args):
    return [MockProtocolOne, MockProtocolTwo]


@pytest.fixture
def modified_loader_single_backend():
    from proton.loader import Loader
    m = Loader.get_all
    Loader.get_all = modified_get_all
    yield Loader
    Loader.get_all = m


class MockBaseNMConnection:
    connection_type = None

    def __init__(self, uuid):
        self.__uuid = uuid

    def get_uuid(self):
        return self.__uuid

    def get_connection_type(self):
        return "vpn"


class MockRegisteredConnection(MockBaseNMConnection):
    pass


class MockActiveConnection(MockBaseNMConnection):
    def get_connection(self):
        return MockRegisteredConnection(self.get_uuid())


class MockNMClient:
    def __init__(self, *args):
        pass

    def get_active_connections(self):
        return [
            MockActiveConnection("test-active-uuid1"),
            MockActiveConnection("test-active-uuid2"),
        ]

    def get_connections(self):
        return [
            MockRegisteredConnection("test-stored-uuid1"),
            MockRegisteredConnection("test-stored-uuid2")
        ]


class BaseMockVpnPlugin:

    @classmethod
    def load_editor_plugin(cls):
        return cls()

    def import_(self, filepath):
        raise NotImplementedError

    @property
    def props(self):
        class PluginInfo:
            def __init__(self, class_name):
                self.class_name = class_name

            @property
            def name(self):
                return self.class_name

        return PluginInfo(type(self).__name__)


class MockVpnPluginOne(BaseMockVpnPlugin):
    def import_(self, filepath):
        if filepath == ".plugin-one":
            return MockConnection()
        else:
            from proton.vpn.backend.linux.networkmanager import networkmanager
            raise networkmanager.gi.repository.GLib.Error()


class MockVpnPluginTwo(BaseMockVpnPlugin):
    def import_(self, filepath):
        if filepath == ".plugin-two":
            return MockConnection()
        else:
            from proton.vpn.backend.linux.networkmanager import networkmanager
            raise networkmanager.gi.repository.GLib.Error()


class MockConnection:

    def normalize(self):
        return True


class MockVpnPluginInfo:

    @staticmethod
    def list_load():
        return [MockVpnPluginOne, MockVpnPluginTwo]


class MockGLib:

    @classmethod
    def run(cls):
        pass

    @classmethod
    def quit(cls):
        pass


class MockVpnConfig:
    def __init__(self, mock_filepath):
        self.mock_filepath = mock_filepath

    def __enter__(self, *args):
        return self.mock_filepath

    def __exit__(self, *args):
        pass


@pytest.fixture
def uninstantiated_patched_nm():
    from proton.vpn.backend.linux.networkmanager import networkmanager

    _nmc = networkmanager.NMClient
    networkmanager.NMClient = MockNMClient

    _glib = networkmanager.GLib
    networkmanager.GLib = MockGLib

    _gi_error = networkmanager.gi.repository.GLib.Error
    networkmanager.gi.repository.GLib.Error = Exception

    _vpnplugin = networkmanager.NM.VpnPluginInfo
    networkmanager.NM.VpnPluginInfo = MockVpnPluginInfo

    networkmanager.LinuxNetworkManager.nm_client = MockNMClient()
    networkmanager.LinuxNetworkManager._persistence_prefix = "mock-prefix_"
    networkmanager.LinuxNetworkManager._unique_id = "mock-unique-id"

    yield networkmanager.LinuxNetworkManager

    networkmanager.LinuxNetworkManager._persistence_prefix = None
    networkmanager.LinuxNetworkManager._unique_id = None
    networkmanager.NMClient = _nmc
    networkmanager.GLib = _glib
    networkmanager.gi.repository.GLib.Error = _gi_error
    networkmanager.NM.VpnPluginInfo = _vpnplugin


# >>>>>>>>>>>>>>>>>>>>>>
# >>>>>>>>>>>>>>>>>>>>>>
# >>>>>>>>>>>>>>>>>>>>>>

def test_init_nm(uninstantiated_patched_nm):
    uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())


def test_get_active_nm_connection(uninstantiated_patched_nm):
    uuid = "test-active-uuid1"
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm._unique_id = uuid
    nm.add_persistence()
    assert nm._get_nm_connection()
    assert nm._unique_id == uuid
    nm.remove_persistence()


def test_persisted_but_not_existing_nm_connection(uninstantiated_patched_nm):
    uuid = "fake-uinque_id"
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm._unique_id = uuid
    nm.add_persistence()
    assert not nm._get_nm_connection()
    assert nm._unique_id == uuid
    nm.remove_persistence()


def test_get_non_persisted_nm_connection(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm._unique_id = "test-active-uuid1"
    assert not nm._get_nm_connection()


def test_start_connection(uninstantiated_patched_nm):
    class TestDummyListenerClass:
        # TO-DO: Find a way to raise the assert at test level since
        # if the test fail, it does not produce a failed tests

        def status_update(self, status):
            assert status.state == states.Connected.state

    def determine_initial_state(self):
        self.update_connection_state(states.Connecting())

    def _start_connection_in_thread(self):
        self.on_event(events.Connected())

    x = uninstantiated_patched_nm.determine_initial_state

    uninstantiated_patched_nm.determine_initial_state = determine_initial_state
    uninstantiated_patched_nm._start_connection_in_thread = _start_connection_in_thread
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())

    start = time.time()
    nm.register(TestDummyListenerClass())

    assert nm.status.state == states.Connecting().state

    nm.start_connection()

    while True:
        if nm.status.state == states.Connected.state:
            break
        elif time.time() - start >= TIMEOUT_LIMIT:
            nm.on_event(events.Timeout())

    uninstantiated_patched_nm.determine_initial_state = x


def test_stop_connection(uninstantiated_patched_nm):
    class TestDummyListenerClass:
        # TO-DO: Find a way to raise the assert at test level since
        # if the test fail, it does not produce a failed tests

        def status_update(self, status):
            assert status.state == states.Disconnected.state

    def determine_initial_state(self):
        self.update_connection_state(states.Disconnecting())

    def _stop_connection_in_thread(self):
        self.on_event(events.Disconnected())

    x = uninstantiated_patched_nm.determine_initial_state
    uninstantiated_patched_nm.determine_initial_state = determine_initial_state

    uninstantiated_patched_nm._stop_connection_in_thread = _stop_connection_in_thread
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())

    start = time.time()
    nm.register(TestDummyListenerClass())

    assert nm.status.state == states.Disconnecting().state

    nm.stop_connection()

    while True:
        if nm.status.state == states.Disconnected().state:
            break
        elif time.time() - start >= TIMEOUT_LIMIT:
            nm.on_event(events.Timeout())

    uninstantiated_patched_nm.determine_initial_state = x


@pytest.mark.parametrize(
    "state, reason, expected_state",
    [
        (
            VPNConnectionStateEnum.IS_ACTIVE,
            VPNConnectionReasonEnum.NOT_PROVIDED,
            states.Connected()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.CONN_ATTEMPT_TO_SERVICE_TIMED_OUT,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.TIMEOUT_WHILE_STARTING_VPN_SERVICE_PROVIDER,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.SECRETS_WERE_NOT_PROVIDED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.SERVER_AUTH_FAILED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.IP_CONFIG_WAS_INVALID,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.SERVICE_PROVIDER_WAS_STOPPED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.CREATE_SOFTWARE_DEVICE_LINK_FAILED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.MASTER_CONN_FAILED_TO_ACTIVATE,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.DELETED_FROM_SETTINGS,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.START_SERVICE_VPN_CONN_SERVICE_FAILED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.VPN_DEVICE_DISAPPEARED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.DEVICE_WAS_DISCONNECTED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.USER_HAS_DISCONNECTED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.UNKNOWN,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.FAILED,
            VPNConnectionReasonEnum.NOT_PROVIDED,
            states.Error()
        ),
        (
            VPNConnectionStateEnum.DISCONNECTED,
            VPNConnectionReasonEnum.NOT_PROVIDED,
            states.Error()
        ),

    ]
)
def test_on_expected_state_changed(uninstantiated_patched_nm, state, reason, expected_state):
    def determine_initial_state(self):
        self.update_connection_state(states.Connecting())

    x = uninstantiated_patched_nm.determine_initial_state
    uninstantiated_patched_nm.determine_initial_state = determine_initial_state

    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm._LinuxNetworkManager__dbus_loop = MockGLib()

    assert nm.status.state == states.Connecting().state

    nm._LinuxNetworkManager__proxy_on_vpn_state_changed(state, reason)
    assert nm.status.state == expected_state.state

    uninstantiated_patched_nm.determine_initial_state = x


@pytest.mark.parametrize("has_connection_been_removed", [True, False])
def test_on_connection_is_removed(uninstantiated_patched_nm, has_connection_been_removed):
    def determine_initial_state(self):
        self.update_connection_state(states.Disconnecting())

    x = uninstantiated_patched_nm.determine_initial_state
    uninstantiated_patched_nm.determine_initial_state = determine_initial_state

    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm._LinuxNetworkManager__dbus_loop = MockGLib()

    assert nm.status.state == states.Disconnecting().state
    nm.on_connection_is_removed(has_connection_been_removed)
    assert nm.status.state == states.Disconnected().state

    uninstantiated_patched_nm.determine_initial_state = x


def test_not_connected_determine_initial_state(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm.determine_initial_state()
    assert nm.status.state == states.Disconnected().state


def test_connected_determine_initial_state(uninstantiated_patched_nm):
    uuid = "test-active-uuid2"
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    nm._unique_id = uuid
    nm.add_persistence()
    assert nm._get_nm_connection()
    assert nm._unique_id == uuid

    nm.determine_initial_state()
    assert nm.status.state == states.Connected().state
    nm.remove_persistence()


def test_get_existing_servername(uninstantiated_patched_nm):
    server = MockVpnServer()
    nm = uninstantiated_patched_nm(server, MockVpnCredentials())
    assert nm._get_servername() == "ProtonVPN {}".format(server.servername)


def test_not_existing_servername(uninstantiated_patched_nm):

    @property
    def servername(self):
        return None

    x = MockVpnServer.servername
    MockVpnServer.servername = servername
    server = MockVpnServer()
    nm = uninstantiated_patched_nm(server, MockVpnCredentials())

    assert nm._get_servername() == "ProtonVPN Connection"

    MockVpnServer.servername = x


def test_not_implemented_setup(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    with pytest.raises(NotImplementedError):
        nm._setup()


def test_get_priority(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    assert isinstance(nm._get_priority(), int)


def test_validate(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    assert nm._validate() is True


def test_import_non_existing_vpn_config(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    with pytest.raises(NotImplementedError):
        nm._import_vpn_config(MockVpnConfig("test"))


def test_import_existing_vpn_config(uninstantiated_patched_nm):
    nm = uninstantiated_patched_nm(MockVpnServer(), MockVpnCredentials())
    assert nm._import_vpn_config(MockVpnConfig(".plugin-two"))


def test_get_non_existing_protocol_from_factory(uninstantiated_patched_nm, modified_loader_single_backend):
    from proton.vpn.connection.exceptions import MissingProtocolDetails
    with pytest.raises(MissingProtocolDetails):
        uninstantiated_patched_nm.factory("non-existing-protocol")


@pytest.mark.parametrize("protocol", ["protocol-one", "protocol-two"])
def test_get_existing_protocol_from_factory(uninstantiated_patched_nm, modified_loader_single_backend, protocol):
    assert uninstantiated_patched_nm.factory(protocol)


def test_get_connection_from_protocol(uninstantiated_patched_nm, modified_loader_single_backend):
    assert uninstantiated_patched_nm._get_connection().status.state == states.Connected().state
