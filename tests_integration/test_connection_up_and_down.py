"""
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
import logging
import os
import subprocess
import threading

import pytest as pytest

from proton.vpn.connection.enum import ConnectionStateEnum

from tests_integration.boilerplate import VPNServer, VPNCredentials, VPNUserPassCredentials, Settings
from tests_integration.protocol import OpenVPNUDP
from tests_integration.utils import get_vpn_client_config, get_vpn_server_by_name

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Default to the atlas environment
proton_api_environment = os.environ.get("PROTON_API_ENVIRONMENT") or "atlas"
os.environ["PROTON_API_ENVIRONMENT"] = proton_api_environment
logger.info(f"Testing on {proton_api_environment} environment.")

VPN_SERVER_NAME = os.environ.get("TEST_VPN_SERVER_NAME") or "DE#999"
logger.info(f"Testing against server {VPN_SERVER_NAME}.")

EXPECTED_CONNECTION_NAME = f"ProtonVPN {VPN_SERVER_NAME}"
from collections import namedtuple


OpenVPNPorts = namedtuple("OpenVPNPorts", "udp tcp")

@pytest.fixture(scope="module")
def vpn_client_config():
    return get_vpn_client_config()


@pytest.fixture(scope="module")
def vpn_server(vpn_client_config):
    server = get_vpn_server_by_name(VPN_SERVER_NAME)
    default_ports = vpn_client_config["OpenVPNConfig"]["DefaultPorts"]

    return VPNServer(
        server_ip=server["Servers"][0]["EntryIP"],
        openvpn_ports=OpenVPNPorts(default_ports["UDP"], default_ports["TCP"]),
        wireguard_ports={},
        domain=server["Domain"],
        servername=server["Name"]
    )


def delete_expected_nm_connection_if_exists():
    os.system(f'nmcli c delete "{EXPECTED_CONNECTION_NAME}" > /dev/null 2>&1')


@pytest.fixture
def test_environment():
    delete_expected_nm_connection_if_exists()
    yield {}
    delete_expected_nm_connection_if_exists()


@pytest.fixture
def openvpn_username():
    # Defaults to the OpenVPN username for the vpnplus user in the atlas environment.
    return os.environ.get("TEST_OPENVPN_USERNAME") or "9rXSJiW7xf5Ffj5K0xuZYTlD"


@pytest.fixture
def openvpn_password():
    # Defaults to the OpenVPN password for the test vpnplus user in the atlas environment.
    return os.environ.get("TEST_OPENVPN_PASSWORD") or "sHwX8ye/ipC9U/OqUTjHRJy/"


def test_networkmanager(test_environment, vpn_server, openvpn_username, openvpn_password):
    vpncredentials = VPNCredentials(
        userpass_credentials=VPNUserPassCredentials(
            username=openvpn_username,
            password=openvpn_password
        )
    )

    nm_protocol = OpenVPNUDP(
        vpnserver=vpn_server,
        vpncredentials=vpncredentials,
        settings=Settings()
    )
    subscriber = Subscriber()
    nm_protocol.register(subscriber)

    logging.info("Connecting...")
    nm_protocol.up()
    logger.info("Waiting for connection...")
    subscriber.wait_for_state(ConnectionStateEnum.CONNECTED, timeout=10)
    assert nm_connection_exists(EXPECTED_CONNECTION_NAME)

    logging.info("Disconnecting...")
    nm_protocol.down()
    logger.info("Waiting for disconnection..")
    subscriber.wait_for_state(ConnectionStateEnum.DISCONNECTED, timeout=10)
    assert not nm_connection_exists(EXPECTED_CONNECTION_NAME)


def nm_connection_exists(connection_name):
    try:
        subprocess.check_output(["nmcli", "connection", "show", connection_name], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        # subprocess.check_output raises this exception when the exit status code of the command it executed is not 0.
        # The nmcli command returns an exit status code of 0 when the connection exists, and 1 otherwise.
        return False


class Subscriber:
    def __init__(self):
        self.state: ConnectionStateEnum = None
        self.events = {state: threading.Event() for state in ConnectionStateEnum}

    def status_update(self, state):
        logging.info(f"status_update({state}")
        self.state = state.state
        self.events[self.state].set()
        self.events[self.state].clear()

    def wait_for_state(self, state: ConnectionStateEnum, timeout: int = None):
        logger.info(f"Waiting for state {state} on event {self.events[state]}.")
        state_reached = self.events[state].wait(timeout)
        if not state_reached:
            raise RuntimeError(f"Time out occurred before reaching state {state.name}.")
