import logging
import os
import subprocess
import sys
import threading

from proton.vpn.connection.enum import ConnectionStateEnum

from tests_integration.boilerplate import VPNServer, VPNCredentials, \
    VPNUserPassCredentials, Settings
from tests_integration.protocol import OpenVPNUDP

logging.basicConfig(level=logging.DEBUG)


logger = logging.getLogger(__name__)

def test_networkmanager(openvpn_username, openvpn_password):
    vpnserver = VPNServer(
        server_ip="185.159.157.129",
        udp_ports=[80, 443, 4569, 1194, 5060, 51820],
        tcp_ports=[443, 5995, 8443, 5060],
        wg_public_key_x25519="",
        domain="node-ch-06.protonvpn.net",
        servername="CH#12"
    )

    vpncredentials = VPNCredentials(
        userpass_credentials=VPNUserPassCredentials(
            username=openvpn_username,
            password=openvpn_password
        )
    )

    nm_protocol = OpenVPNUDP(
        vpnserver=vpnserver,
        vpncredentials=vpncredentials,
        settings=Settings()
    )
    subscriber = Subscriber()
    nm_protocol.register(subscriber)

    logging.info("Connecting...")
    nm_protocol.up()
    logger.info("Waiting for connection...")
    subscriber.wait_for_state(ConnectionStateEnum.CONNECTED, timeout=10)
    assert nm_connection_exists(f"ProtonVPN {vpnserver.servername}")

    logging.info("Disconnecting...")
    nm_protocol.down()
    logger.info("Waiting for disconnection..")
    subscriber.wait_for_state(ConnectionStateEnum.DISCONNECTED, timeout=10)
    assert not nm_connection_exists(f"ProtonVPN {vpnserver.servername}")


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
        logging.info(f"waiting for state {state} on event {self.events[state]}.")
        state_reached = self.events[state].wait(timeout)
        if not state_reached:
            raise RuntimeError(f"Time out occurred before reaching state {state.name}.")


if __name__ == "__main__":
    try:
        subprocess.check_output(["nmcli", "--help"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise RuntimeError("The command line nmcli program is required.")

    openvpn_username = sys.argv[1] if len(sys.argv) == 3 else os.environ.get("OPENVPN_USERNAME")
    openvpn_password = sys.argv[2] if len(sys.argv) == 3 else os.environ.get("OPENVPN_PASSWORD")
    if not openvpn_username and not openvpn_password:
        raise RuntimeError(f"Usage: {sys.argv[0]} OPENVPN_USERNAME OPENVPN_PASSWORD")

    test_networkmanager(
        openvpn_username=openvpn_username,
        openvpn_password=openvpn_password
    )
