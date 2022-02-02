from proton.vpn.backend.linux.networkmanager import LinuxNetworkManager


class OpenVPN(LinuxNetworkManager):
    virtual_device_name = "proton0"
    connection = None

    @staticmethod
    def get_by_protocol(protocol: str):
        """Get VPN connection based on protocol."""
        if "tcp" in protocol.lower():
            return OpenVPNTCP
        else:
            return OpenVPNUDP

    def _configure_connection(self, vpnconfig):
        """Configure imported vpn connection.

            :param vpnconfig: vpn configuration object.
            :type vpnconfig: VPNConfiguration

        It also uses vpnserver, vpncredentials and settings for the following reasons:
            - vpnserver is used to fetch domain, servername (optioanl)
            - vpncredentials is used to fetch username/password for non-certificate based connections
            - settings is used to fetch dns settings
        """
        self.connection = self._import_vpn_config(vpnconfig)

        self.__vpn_settings = self.connection.get_setting_vpn()
        self.__connection_settings = self.connection.get_setting_connection()

        self._unique_id = self.__connection_settings.get_uuid()

        self.__make_vpn_user_owned()
        self.__add_server_certificate_check()
        self.__configure_dns()
        self.__set_custom_connection_id()

        if not vpnconfig.use_certificate:
            self.__add_vpn_credentials()

    def __make_vpn_user_owned(self):
        # returns NM.SettingConnection
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingConnection.html#NM.SettingConnection
        from getpass import getuser

        self.__connection_settings.add_permission(
            "user",
            getuser(),
            None
        )

    def __add_server_certificate_check(self):
        appened_domain = "name:" + self._vpnserver.domain
        self.__vpn_settings.add_data_item(
            "verify-x509-name", appened_domain
        )

    def __configure_dns(self):
        """Apply dns configurations to ProtonVPN connection."""

        ipv4_config = self.connection.get_setting_ip4_config()
        ipv6_config = self.connection.get_setting_ip6_config()

        ipv4_config.props.dns_priority = -1500
        ipv6_config.props.dns_priority = -1500

        try:
            if len(self._settings.dns_custom_ips) == 0:
                return
        except AttributeError:
            return

        custom_dns = self.settings.dns_custom_ips
        ipv4_config.props.ignore_auto_dns = True
        ipv6_config.props.ignore_auto_dns = True

        ipv4_config.props.dns = custom_dns

    def __set_custom_connection_id(self):
        self.__connection_settings.props.id = self._get_servername()

    def __add_vpn_credentials(self):
        """Add OpenVPN credentials to ProtonVPN connection.

        Args:
            openvpn_username (string): openvpn/ikev2 username
            openvpn_password (string): openvpn/ikev2 password
        """
        # returns NM.SettingVpn if the connection contains one, otherwise None
        # https://lazka.github.io/pgi-docs/NM-1.0/classes/SettingVpn.html
        username, password = self._get_user_pass(True)

        self.__vpn_settings.add_data_item(
            "username", username
        )
        self.__vpn_settings.add_secret(
            "password", password
        )

    def down(self):
        self._remove_connection_async(self._get_protonvpn_connection(True))


class OpenVPNTCP(OpenVPN):
    """Creates a OpenVPNTCP connection."""
    protocol = "openvpn_tcp"
    _persistence_prefix = "nm_{}_".format(protocol)

    def _setup(self):
        from proton.vpn.connection.vpnconfiguration import VPNConfiguration
        vpnconfig = VPNConfiguration.from_factory(self.protocol)
        vpnconfig = vpnconfig(self._vpnserver, self._vpncredentials, self._settings)
        vpnconfig.use_certificate = self._use_certificate

        self._configure_connection(vpnconfig)
        self._add_connection_async(self.connection)


class OpenVPNUDP(OpenVPN):
    """Creates a OpenVPNUDP connection."""
    protocol = "openvpn_udp"
    _persistence_prefix = "nm_{}_".format(protocol)

    def _setup(self):
        from .vpnconfiguration import VPNConfiguration
        vpnconfig = VPNConfiguration.from_factory(self.protocol)
        vpnconfig = vpnconfig(self._vpnserver, self._vpncredentials, self._settings)
        vpnconfig.use_certificate = self._use_certificate

        self._configure_connection(vpnconfig)
        self._add_connection_async(self.connection)
