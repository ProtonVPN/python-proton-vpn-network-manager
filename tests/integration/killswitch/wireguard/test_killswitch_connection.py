import os

import pytest
import subprocess

from proton.vpn.backend.linux.networkmanager.killswitch.wireguard.killswitch_connection import KillSwitchGeneralConfig
from proton.vpn.backend.linux.networkmanager.killswitch.wireguard.killswitch_connection_handler import KillSwitchConnectionHandler

TEST_CONFIG = KillSwitchGeneralConfig(
    human_readable_id="test-pvpn-killswitch",
    interface_name="testpvpn0"
)


def _assert_connection_exist():
    output = int(os.system(f"nmcli -g GENERAL.STATE c s \"{TEST_CONFIG.human_readable_id}\""))
    assert output == 0


def _assert_connection_does_not_exist():
    output = int(os.system(f"nmcli -g GENERAL.STATE c s \"{TEST_CONFIG.human_readable_id}\""))
    assert output != 0


def _nmcli_del_connection():
    os.system(f"nmcli c del {TEST_CONFIG.human_readable_id}")


class TestIntegrationKillSwitchConnectionHandler:
    def setup_class(cls):
        _nmcli_del_connection()
        _assert_connection_does_not_exist()

    def teardown_class(cls):
        _nmcli_del_connection()
        _assert_connection_does_not_exist()

    @pytest.fixture
    def cleanup_env(self):
        yield {}
        _nmcli_del_connection()
        _assert_connection_does_not_exist()

    @pytest.fixture
    def test_killswitch_config(self):
        cfg = KillSwitchGeneralConfig(
            human_readable_id=TEST_CONFIG.human_readable_id,
            interface_name=TEST_CONFIG.interface_name
        )
        yield cfg

    def _nmcli_add_connection(self):
        os.system(f"nmcli c a type dummy ifname {TEST_CONFIG.human_readable_id} con-name {TEST_CONFIG.human_readable_id}")

    def get_ipv4_addresses(self):
        nmcli_string = f"nmcli -g ipv4.addresses c s {TEST_CONFIG.human_readable_id}"
        ipv4_addresses = subprocess.check_output(nmcli_string.split(" ")).decode().strip("\n").split(",")
        ipv4_addresses = tuple([addr.replace(" ", "") for addr in ipv4_addresses])
        return ipv4_addresses

    @pytest.mark.asyncio
    async def test_add_and_remove_connection(self, cleanup_env, test_killswitch_config):
        handler = KillSwitchConnectionHandler(config=test_killswitch_config)
        await handler.add_kill_switch_connection(permanent=False)
        _assert_connection_exist()
        await handler.remove_killswitch_connection()
        _assert_connection_does_not_exist()
