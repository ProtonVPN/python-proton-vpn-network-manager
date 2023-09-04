"""
Utility module to do TCP connection checks.
"""
import time
import ipaddress
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from threading import Thread
from typing import Callable, List, Union

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5


def _get_address_family(
        ip_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
) -> socket.AddressFamily:  # pylint: disable=no-member
    if isinstance(ip_address, ipaddress.IPv4Address):
        return socket.AF_INET
    if isinstance(ip_address, ipaddress.IPv6Address):
        return socket.AF_INET6
    raise TypeError(f"Invalid IP address: {ip_address}")


def is_port_reachable(
        ip_address: str, port: str, timeout_in_secs: int = DEFAULT_TIMEOUT
) -> bool:
    """
    Checks if the specified IP address is reachable by opening a TCP socket
    to the specified port.

    :param ip_address: IP address to connect to.
    :param port: TCP port to connect to.
    :param timeout_in_secs: Optional connection timeout.
    :returns: True if a socket could be opened to the specified address/port,
        or False otherwise.
    """
    ip_address = ipaddress.ip_address(ip_address)
    address_family = _get_address_family(ip_address)

    logger.debug("Checking %s:%s...", ip_address, port)
    with closing(socket.socket(address_family, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout_in_secs)
        socket_result = sock.connect_ex((f"{ip_address}", port))
        logger.debug("%s:%s => %s", ip_address, port, socket_result)
        return socket_result == 0


def is_any_port_reachable(
        ip_address: str, ports: List[str], timeout: int = DEFAULT_TIMEOUT
) -> bool:
    """
    Checks if the specified IP address is reachable by opening a TCP socket
    to any of the specified ports.

    All ports are probed in parallel. As soon as a socket is opened to
    one of them, connectivity is reported by returning True. If all
    the connections to the different ports fail, then False is returned.

    :param ip_address: IP address to connect to.
    :param port: TCP ports to try to connect to.
    :param timeout_in_secs: Optional connection timeout.
    :returns: True if a socket could be opened to the specified address/ports,
        or False otherwise.
    """
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(is_port_reachable, ip_address, port, timeout) for port in ports]
        for future in as_completed(futures):
            if not future.exception() and future.result():
                return True

    return False


def is_any_port_reachable_async(
        ip_address: str, ports: List[str], callback: Callable, timeout: int = DEFAULT_TIMEOUT
) -> None:
    """
    Asynchronous version of `is_any_port_reachable`. The specified `callback` is called with
    an argument: True if the one of the ports was reachable or False otherwise.
    """
    def _check_connectivity():
        # FIX-ME: Since we're adding kill switch connections, it sometimes it
        # takes some milliseconds until they're enabled after they have been added,
        # thus we need to introduce an artificial delay to ensure that the kill
        # switch connection have been added and connected, and only then
        # we should attempt to do a tcp check.
        time.sleep(2)
        callback(is_any_port_reachable(ip_address, ports, timeout))

    Thread(target=_check_connectivity, daemon=True).start()
