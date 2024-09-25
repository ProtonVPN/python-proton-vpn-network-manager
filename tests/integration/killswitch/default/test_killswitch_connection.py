import pytest
import subprocess

from proton.vpn.backend.linux.networkmanager.killswitch.default.killswitch_connection_handler import KillSwitchConnectionHandler

FULL_KS_CONNECTION_ID = "test-killswitch"
ROUTED_KS_CONNECTION_ID = "test-routed-killswitch"
IPV6_KS_CONNECTION_ID = "test-killswitch-ipv6"
TEST_INTERFACE_NAME = "testpvpn0"


def _assert_connection_exist(connection_id):
    subprocess.run(
        ["nmcli", "-g", "GENERAL.STATE", "c", "s", f"{connection_id}"],
        capture_output=True, check=True
    )


def _assert_connection_does_not_exist(connection_id):
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            ["nmcli", "-g", "GENERAL.STATE", "c", "s", f"{connection_id}"],
            capture_output=True, check=True
        )


def _nmcli_add_connection(connection_id):
    subprocess.run(
        [
            "nmcli", "c", "a", "type", "dummy", "ifname", f"{TEST_INTERFACE_NAME}",
            "con-name", f"{connection_id}"
        ],
        capture_output=True, check=True
    )


def _nmcli_del_connection(connection_id):
    subprocess.run(["nmcli", "c", "del", f"{connection_id}"], capture_output=True)


@pytest.fixture
def cleanup_env():
    _nmcli_del_connection(FULL_KS_CONNECTION_ID)
    _nmcli_del_connection(ROUTED_KS_CONNECTION_ID)
    _nmcli_del_connection(IPV6_KS_CONNECTION_ID)
    yield {}
    _nmcli_del_connection(FULL_KS_CONNECTION_ID)
    _nmcli_del_connection(ROUTED_KS_CONNECTION_ID)
    _nmcli_del_connection(IPV6_KS_CONNECTION_ID)


@pytest.mark.asyncio
async def test_add_full_killswitch_connection(cleanup_env):
    handler = KillSwitchConnectionHandler(connection_prefix="test")
    await handler.add_full_killswitch_connection(permanent=False)
    _assert_connection_exist(FULL_KS_CONNECTION_ID)


@pytest.mark.asyncio
async def test_remove_full_killswitch_connection(cleanup_env):
    _nmcli_add_connection(FULL_KS_CONNECTION_ID)
    handler = KillSwitchConnectionHandler(connection_prefix="test")
    await handler.remove_full_killswitch_connection()
    _assert_connection_does_not_exist(FULL_KS_CONNECTION_ID)


@pytest.mark.asyncio
async def test_add_routed_killswitch_connection(cleanup_env):
    handler = KillSwitchConnectionHandler(connection_prefix="test")
    await handler.add_routed_killswitch_connection(server_ip="192.168.1.1", permanent=False)
    _assert_connection_exist(ROUTED_KS_CONNECTION_ID)


@pytest.mark.asyncio
async def test_remove_routed_killswitch_connection(cleanup_env):
    _nmcli_add_connection(ROUTED_KS_CONNECTION_ID)
    handler = KillSwitchConnectionHandler(connection_prefix="test")
    await handler.remove_routed_killswitch_connection()
    _assert_connection_does_not_exist(ROUTED_KS_CONNECTION_ID)


@pytest.mark.asyncio
async def test_add_ipv6_killswitch_connection(cleanup_env):
    handler = KillSwitchConnectionHandler(connection_prefix="test")
    await handler.add_ipv6_leak_protection()
    _assert_connection_exist(IPV6_KS_CONNECTION_ID)


@pytest.mark.asyncio
async def test_remove_routed_killswitch_connection(cleanup_env):
    _nmcli_add_connection(IPV6_KS_CONNECTION_ID)
    handler = KillSwitchConnectionHandler(connection_prefix="test")
    await handler.remove_ipv6_leak_protection()
    _assert_connection_does_not_exist(IPV6_KS_CONNECTION_ID)
