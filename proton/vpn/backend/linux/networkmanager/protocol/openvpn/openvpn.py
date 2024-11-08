"""
OpenVPN protocol implementations.


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

from concurrent.futures import Future
import os
from getpass import getuser
from ipaddress import IPv4Address, IPv6Address

from gi.repository import NM
import gi
from proton.vpn.backend.linux.networkmanager.core import LinuxNetworkManager
from proton.vpn.connection.vpnconfiguration import VPNConfiguration
gi.require_version("NM", "1.0")


class OpenVPN(LinuxNetworkManager):
    """Base class for the backends implementing the OpenVPN protocols."""
    DNS_PRIORITY = -1500
    VIRTUAL_DEVICE_NAME = "proton0"
    connection = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vpn_settings = None
        self._connection_settings = None

    def setup(self) -> Future:
        """Methods that creates and applies any necessary changes to the connection."""
        self._generate_connection()
        self._modify_connection()
        return self.nm_client.add_connection_async(self.connection)

    def _generate_connection(self):
        vpnconfig = VPNConfiguration.from_factory(self.protocol)(
            self._vpnserver, self._vpncredentials, self._settings, self._use_certificate
        )

        self.connection = self._import_vpn_config(vpnconfig)

        self._unique_id = self.connection.get_uuid()
        self._vpn_settings = self.connection.get_setting_vpn()
        self._connection_settings = self.connection.get_setting_connection()

    def _modify_connection(self):
        """Configure imported vpn connection.
        """
        self._set_custom_connection_id()
        self._set_connection_user_owned()
        self._set_server_certificate_check()
        self._set_dns()
        if not self._use_certificate:
            self._set_vpn_credentials()

        self.connection.add_setting(self._connection_settings)

    def _set_custom_connection_id(self):
        self._connection_settings.set_property(NM.SETTING_CONNECTION_ID, self._get_servername())

    def _set_connection_user_owned(self):
        # returns NM.SettingConnection
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingConnection.html#NM.SettingConnection

        self._connection_settings.add_permission(
            NM.SETTING_USER_SETTING_NAME,
            getuser(),
            None
        )

    def _set_server_certificate_check(self):
        appened_domain = "name:" + self._vpnserver.domain
        self._vpn_settings.add_data_item(
            "verify-x509-name", appened_domain
        )

    def _set_dns(self):
        """Apply dns configurations to ProtonVPN connection."""
        # pylint: disable=duplicate-code
        ipv4_config = self.connection.get_setting_ip4_config()
        ipv6_config = self.connection.get_setting_ip6_config()

        self.configure_dns(
            nm_setting=ipv4_config,
            ip_version=IPv4Address,
            connection_settings=self._connection_settings
        )

        if self.enable_ipv6_support:
            self.configure_dns(
                nm_setting=ipv6_config,
                ip_version=IPv6Address,
                connection_settings=self._connection_settings
            )
        else:
            ipv6_config.set_property(NM.SETTING_IP_CONFIG_DNS_PRIORITY, self.DNS_PRIORITY)
            ipv6_config.set_property(NM.SETTING_IP_CONFIG_IGNORE_AUTO_DNS, True)

        self.connection.add_setting(ipv4_config)
        self.connection.add_setting(ipv6_config)

    def _set_vpn_credentials(self):
        """Add OpenVPN credentials to ProtonVPN connection.

        Args:
            openvpn_username (string): openvpn/ikev2 username
            openvpn_password (string): openvpn/ikev2 password
        """
        # returns NM.SettingVpn if the connection contains one, otherwise None
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingVpn.html
        username, password = self._get_user_pass(True)

        self._vpn_settings.add_data_item(
            "username", username
        )
        # Use System wide password if we are root (No Secret Agent)
        # See https://people.freedesktop.org/~lkundrak/nm-docs/nm-settings.html#secrets-flags
        # => Allow headless testing
        if os.getuid() == 0:
            self._vpn_settings.add_data_item("password-flags", "0")
        self._vpn_settings.add_secret(
            "password", password
        )


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "openvpn-tcp"
    ui_protocol = "OpenVPN (TCP)"

    @classmethod
    def _get_priority(cls):
        return 1

    @classmethod
    def _validate(cls):
        # FIX ME: This should do a validation to ensure that NM can be used
        return True


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "openvpn-udp"
    ui_protocol = "OpenVPN (UDP)"

    @classmethod
    def _get_priority(cls):
        return 1

    @classmethod
    def _validate(cls):
        # FIX ME: This should do a validation to ensure that NM can be used
        return True
