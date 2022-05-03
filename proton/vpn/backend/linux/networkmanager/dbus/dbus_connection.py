import dbus

__all__ = ["DbusConnection"]


class DbusConnection:
    def __init__(self):
        self.__connection_settings = DbusConnectionSettings(
            "human_readable_id", "interface_name"
        )
        self.__ipv4_settings = DbusIpv4Settings()
        self.__ipv6_settings = DbusIpv6Settings()
        self.__wireguard = DbusWireguard()

    def generate_configuration(self):
        cfg = dbus.Dictionary({
            'connection': self.__connection_settings.generate_configuration(),
            'ipv4': self.__ipv4_settings.generate_configuration(),
            'ipv6': self.__ipv6_settings.generate_configuration(),
        })

        if self.__connection_settings.connection_type == "wireguard":
            try:
                cfg["wireguard"] = self.__wireguard.generate_configuration()
            except AssertionError:
                raise RuntimeError("Wireguard configurations is missing peers/keys")

        return cfg

    @property
    def settings(self) -> "DbusConnectionSettings":
        return self.__connection_settings

    @property
    def ipv4(self) -> "DbusIpv4Settings":
        return self.__ipv4_settings

    @property
    def ipv6(self) -> "DbusIpv6Settings":
        return self.__ipv6_settings

    @property
    def wireguard(self) -> "DbusWireguard":
        return self.__wireguard


class DbusConnectionSettings:
    def __init__(self, human_readable_id, interface_name, connection_type="dummy", unique_id=None):
        if not unique_id:
            import uuid
            unique_id = str(uuid.uuid1())

        self.__connection_type = connection_type
        self.__human_readable_id = human_readable_id
        self.__unique_id = unique_id
        self.__interface_name = interface_name

    def generate_configuration(self):
        cfg = dbus.Dictionary({"type": self.__connection_type})

        if self.unique_id:
            cfg["uuid"] = self.unique_id

        if self.human_readable_id:
            cfg["id"] = self.human_readable_id

        if self.interface_name:
            cfg["interface-name"] = self.interface_name

        return cfg

    @property
    def connection_type(self) -> str:
        return self.__connection_type

    @connection_type.setter
    def connection_type(self, newvalue: str):
        assert newvalue in ["vpn", "bridge", "wireguard", "dummy"]
        self.__connection_type = newvalue

    @property
    def unique_id(self) -> str:
        return self.__unique_id

    @unique_id.setter
    def unique_id(self, newvalue: str):
        self.__unique_id = newvalue

    @property
    def human_readable_id(self) -> str:
        return self.__human_readable_id

    @human_readable_id.setter
    def human_readable_id(self, newvalue: str):
        self.__human_readable_id = newvalue

    @property
    def interface_name(self) -> str:
        return self.__interface_name

    @interface_name.setter
    def interface_name(self, newvalue: str):
        self.__interface_name = newvalue


class DbusWireguard:
    """
    Source: https://developer-old.gnome.org/NetworkManager/stable/settings-wireguard.html
    """
    def __init__(self):
        self.__peers = None
        self.__private_key = None

    def generate_configuration(self):
        cfg = dbus.Dictionary({})

        if self.peers:
            cfg["peers"] = self.peers

        if self.private_key:
            cfg["private-key"] = self.private_key

        assert "peers" in cfg
        assert "private-key" in cfg

        return cfg

    @property
    def private_key(self) -> str:
        return self.__private_key

    @private_key.setter
    def private_key(self, newvalue: str):
        """
        :param newvalue: The 256 bit private-key in base64 encoding
        :type newvalue: str
        """
        self.__private_key = newvalue

    @property
    def peers(self) -> list:
        return self.__peers

    @peers.setter
    def peers(self, newvalue: list):
        """Wireguard specific

        :param newvalue: List of peers. Each peer is adict
        :type newvalue: list(dict)

        Expected format:

        .. code-block::
            peers = [
                {
                    allowed-ips: ["0.0.0.0/0", ...],
                    endpoint: "192.168.0.1:443"
                    public_key: "generated-private-key"
                },
                ...
            ]
        """
        if newvalue is None:
            self.__peers = None
            return

        _peers = []
        for peer in newvalue:
            self.__ensure_peer_has_expected_keywords(peer)
            _peer_dict = {}

            for k, v in peer.items():
                _peer_dict[k] = self.__parse_peer_value(k, v)

            _peers.append(
                dbus.Dictionary(
                    _peer_dict,
                    signature=dbus.Signature("sv")
                )
            )

        self.__peers = dbus.Array(
            _peers,
            signature=dbus.Signature("a{sv}")
        )

    def __ensure_peer_has_expected_keywords(self, peer):
        assert "allowed-ips" in peer
        assert "endpoint" in peer
        assert "public-key" in peer

    def __parse_peer_value(self, peer_key, peer_value):
        new_value = None
        if peer_key == "allowed-ips":
            new_value = dbus.Array(
                peer_value if isinstance(peer_value, list) else list(peer_value),
                signature=dbus.Signature("s")
            )
        elif peer_key == "endpoint":
            # FIX-ME: ensure that the ip is in expected format
            pass

        return peer_value if not new_value else new_value


class BaseDbusIpSettings:
    """
    Sources:
        https://developer-old.gnome.org/NetworkManager/stable/settings-ipv4.html
        https://developer-old.gnome.org/NetworkManager/stable/settings-ipv6.html
    """
    ip_version = None

    def __init__(self):
        if not self.ip_version:
            raise RuntimeError("IP version not set")

        self.__address_data = None
        self.__method = None
        self.__dns = None
        self.__dns_priority = None
        self.__dns_search = None
        self.__gateway = None
        self.__ignore_auto_dns = None
        self.__route_metric = None
        self.__addresses = None
        self.__route_data = None

    def generate_configuration(self):
        cfg = dbus.Dictionary({})

        if self.address_data:
            cfg["address-data"] = self.address_data

        if self.method:
            cfg["method"] = self.method

        if self.dns_priority:
            cfg["dns-priority"] = self.dns_priority

        if self.dns_search:
            cfg["dns-search"] = self.dns_search

        if self.gateway:
            cfg["gateway"] = self.gateway

        if self.ignore_auto_dns:
            cfg["ignore-auto-dns"] = self.ignore_auto_dns

        if self.route_metric:
            cfg["route-metric"] = self.route_metric

        if self.addresses:
            cfg["addresses"] = self.addresses

        if self.route_data:
            cfg["route-data"] = self.route_data

        if self.dns:
            cfg["dns"] = self.dns

        if len(cfg) == 0:
            if self.ip_version == 4:
                raise RuntimeError("IPv4 must be defined")

            cfg["method"] = "ignore"

        return cfg

    @staticmethod
    def ipv4_to_int(ipv4_addr: str) -> int:
        """
            :return: ipv4 transformed into byte value
            :rtype: int
        """
        import ipaddress
        return int.from_bytes(ipaddress.ip_address(ipv4_addr).packed, 'big')

    @staticmethod
    def ipv6_to_byte_list(ipv6_addr: str) -> list:
        """
            :return: ipv6 transformed into list with dbus.Byte
            :rtype: list
        """
        import dbus
        import ipaddress
        return [
            dbus.Byte(n) for n in list(ipaddress.ip_address(ipv6_addr).packed)
        ]

    @property
    def address_data(self) -> dict:
        return self.__address_data

    @address_data.setter
    def address_data(self, newvalue: dict):
        """
            :param newvalue: dict with keywords `address` and `prefix`
            :type type: dict

        Array of IPv4/6 addresses. Each address dictionary contains
        at least 'address' and 'prefix' entries, containing the IP address
        as a string, and the prefix length as a uint32. Additional attributes
        may also exist on some addresses.

        Expected format:

        .. code-block::
            address_data = {"address": "192.168.1.205", "prefix": 24}
        """
        assert newvalue.get("address")
        assert newvalue.get("prefix")

        self.__address_data = dbus.Array([dbus.Dictionary(newvalue)], signature=dbus.Signature("a{sv}"))

    @property
    def method(self) -> str:
        return self.__method

    @method.setter
    def method(self, newvalue: str):
        """
            :param newvalue: how this settings will act
            :type type: str

        IP configuration method. NMSettingIP4Config and NMSettingIP6Config both support
        "disabled", "auto", "manual", and "link-local".
        See the subclass-specific documentation for other values.
        In general, for the "auto" method, properties such as "dns" and "routes" specify
        information that is added on to the information returned from automatic configuration.
        The "ignore-auto-routes" and "ignore-auto-dns" properties modify this behavior.
        For methods that imply no upstream network, such as "shared" or "link-local",
        these properties must be empty. For IPv4 method "shared", the IP subnet can be configured
        by adding one manual IPv4 address or otherwise 10.42.x.0/24 is chosen. Note that the shared method
        must be configured on the interface which shares the internet to a subnet,
        not on the uplink which is shared.
        """
        assert newvalue in ["disabled", "auto", "manual", "link-local"]
        self.__method = newvalue

    @property
    def dns(self) -> list:
        return self.__dns

    @dns.setter
    def dns(self, newvalue: list):
        """
            :param newvalue:  list of IP addresses of DNS servers
            :type type: list(str)
        """
        if self.ip_version == 4:
            ipv4_dns = []
            for entry in newvalue:
                ipv4_dns.append(BaseDbusIpSettings.ipv4_to_int(entry))

            dns_addresses = dbus.Array(ipv4_dns, signature=dbus.Signature('u'))
        else:
            ipv6_dns = []
            for entry in newvalue:
                ipv6_dns.append(
                    dbus.Array(BaseDbusIpSettings.ipv6_to_byte_list(entry), signature=dbus.Signature('y'))
                )

            dns_addresses = dbus.Array(ipv6_dns, signature=dbus.Signature('ay'))

        self.__dns = dns_addresses

    @property
    def dns_priority(self) -> int:
        return self.__dns_priority

    @dns_priority.setter
    def dns_priority(self, newvalue: int):
        """
            :param newvalue: the priority value for dns.
                The lower the value the higher the priority.
            :type type: int

        DNS servers priority. The relative priority for DNS servers specified by this setting.
        A lower numerical value is better (higher priority). Negative values have the special
        effect of excluding other configurations with a greater numerical priority value;
        so in presence of at least one negative priority, only DNS servers from connections
        with the lowest priority value will be used. To avoid all DNS leaks,
        set the priority of the profile that should be used to the most negative value of all active connections profiles.
        Zero selects a globally configured default value. If the latter is missing or zero too,
        it defaults to 50 for VPNs (including WireGuard) and 100 for other connections.
        Note that the priority is to order DNS settings for multiple active connections.
        It does not disambiguate multiple DNS servers within the same connection profile.
        When multiple devices have configurations with the same priority, VPNs will be considered first,
        then devices with the best (lowest metric) default route and then all other devices.
        When using dns=default, servers with higher priority will be on top of resolv.conf.
        To prioritize a given server over another one within the same connection,
        just specify them in the desired order. Note that commonly the resolver tries
        name servers in /etc/resolv.conf in the order listed, proceeding with the next server in the list on failure.
        See for example the "rotate" option of the dns-options setting.
        If there are any negative DNS priorities, then only name servers from the devices with that lowest priority will be considered.
        When using a DNS resolver that supports Conditional Forwarding or Split DNS (with dns=dnsmasq or dns=systemd-resolved settings),
        each connection is used to query domains in its search list.
        The search domains determine which name servers to ask, and the DNS priority is used to prioritize
        name servers based on the domain. Queries for domains not present in any search list are routed
        through connections having the '~.' special wildcard domain, which is added automatically to
        connections with the default route (or can be added manually).
        When multiple connections specify the same domain, the one with 
        the best priority (lowest numerical value) wins. If a sub domain is configured on another interface
        it will be accepted regardless the priority, unless parent domain on the other interface has a negative priority,
        which causes the sub domain to be shadowed. With Split DNS one can avoid undesired DNS leaks by properly
        configuring DNS priorities and the search domains, so that only name servers of the desired interface are configured.
        """
        self.__dns_priority = int(newvalue)

    @property
    def dns_search(self) -> list:
        return self.__dns_search

    @dns_search.setter
    def dns_search(self, newvalue: list):
        """
            :param newvalue: list with strings for dns search
            :type newvalue: list(str)

        Array of DNS search domains. Domains starting with a tilde ('~') are considered 'routing' domains
        and are used only to decide the interface over which a query must be forwarded; they are not used
        to complete unqualified host names. When using a DNS plugin that supports Conditional Forwarding
        or Split DNS, then the search domains specify which name servers to query. This makes the behavior
        different from running with plain /etc/resolv.conf. For more information see also the dns-priority
        setting.
        """
        self.__dns_search = dbus.Array(newvalue)

    @property
    def gateway(self) -> str:
        return self.__gateway

    @gateway.setter
    def gateway(self, newvalue: str):
        """
            :param newvalue: geteway string
            :type newvalue: str

        The gateway associated with this configuration. This is only meaningful if "addresses" is also set.
        The gateway's main purpose is to control the next hop of the standard default route on the device.
        Hence, the gateway property conflicts with "never-default" and will be automatically dropped
        if the IP configuration is set to never-default. As an alternative to set the gateway,
        configure a static default route with /0 as prefix length.
        """
        self.__gateway = str(newvalue)

    @property
    def ignore_auto_dns(self) -> bool:
        return self.__ignore_auto_dns

    @ignore_auto_dns.setter
    def ignore_auto_dns(self, newvalue: bool):
        """
            :param newvalue: if auto dns should be ignored or not
            :type newvalue: bool

        When "method" is set to "auto" and this property to TRUE,
        automatically configured name servers and search domains are ignored
        and only name servers and search domains specified
        in the "dns" and "dns-search" properties, if any, are used.
        """
        self.__ignore_auto_dns = bool(newvalue)

    @property
    def route_metric(self) -> int:
        return self.__route_metric

    @route_metric.setter
    def route_metric(self, newvalue: int):
        """
            :param newvalue: priority value for this setting
            :type newvalue: int

        The default metric for routes that don't explicitly specify a metric.
        The default value -1 means that the metric is chosen automatically based on the device type.
        The metric applies to dynamic routes, manual (static) routes that don't have an explicit metric setting,
        address prefix routes, and the default route. Note that for IPv6,
        the kernel accepts zero (0) but coerces it to 1024 (user default).
        Hence, setting this property to zero effectively mean setting it to 1024.
        For IPv4, zero is a regular value for the metric.
        """
        self.__route_metric = int(newvalue)

    @property
    def addresses(self) -> list:
        return self.__addresses

    @addresses.setter
    def addresses(self, newvalue: list):
        """
        :param newvalue: a list with touple values
        :type newvalue: list

        Expected format:

        .. code-block::
            # ipv4
            addresses = [("192.1.168.1", 24, "192.1.168.1"), ...]

            # ipv6
            addresses = [("fdeb:446c:912d:08da::", 64, "fdeb:446c:912d:08da::1"), ...]

        Ensure that (within each tuple):
         - 1st param:  a string of the ip
         - 2nd param:  network prefix (unsigned 32 int)
         - 3rd param:  gateway in string format
        ---
        Implementation details:

        For ipv6 `addressess` the container has to be a dbus.Struct with signature (ayuay),
        where the:
         - `ay`:   the server ipv6 transformed to byte list (u8 list)
         - `u`:    the network prefix (/8, /16, /32, etc)
         - `ay`:   the ipv6 gateway transformed to byte list (u8 list)
        Here's a suggestion on how to build:

        .. code-block::
            addresses_ipv6 = dbus.Struct(
                (
                    [ dbus.Byte(n) for n in list(ipaddress.ip_address(ipv6_addr).packed) ],
                    dbus.UInt32(64),
                    [ dbus.Byte(n) for n in list(ipaddress.ip_address(ipv6_addr).packed) ]
                )
        ---
        For ipv4 is much simplier but the structure is generally the same. Instead of a `dbus.Struct`
        an `dbus.Array` is used instead to store first: the server IP, then the prefix and lastly the
        gateway IP. Here is an example:

        .. code-block::
            addresses_ipv4 = dbus.Array(
                [
                    int.from_bytes(ipaddress.ip_address(ipv4_addr).packed, 'big'),
                    dbus.UInt32(24),
                    int.from_bytes(ipaddress.ip_address(ipv4_addr).packed, 'big')
                ], signature=dbus.Signature('u')
            )
        """
        if self.ip_version == 4:
            ipv4_addresses = []
            for entry in newvalue:
                server_ip = entry[0]
                cidr = entry[1]
                gateway = entry[2]

                ipv4_addresses.append(
                    dbus.Array(
                        [
                            BaseDbusIpSettings.ipv4_to_int(server_ip),
                            dbus.UInt32(int(cidr)),
                            BaseDbusIpSettings.ipv4_to_int(gateway)
                        ], signature=dbus.Signature('u')
                    )
                )
            self.__addresses = dbus.Array(ipv4_addresses, signature=dbus.Signature('au'))
        else:
            ipv6_addresses = []
            for entry in newvalue:
                server_ip = entry[0]
                cidr = entry[1]
                gateway = entry[2]

                ipv6_addresses.append(
                    dbus.Struct(
                        (
                            BaseDbusIpSettings.ipv6_to_byte_list(server_ip),
                            dbus.UInt32(int(cidr)),
                            BaseDbusIpSettings.ipv6_to_byte_list(gateway)
                        )
                    )
                )
            self.__addresses = dbus.Array(ipv6_addresses)

    @property
    def route_data(self):
        return self.__route_data

    @route_data.setter
    def route_data(self, newvalue: list):
        if newvalue is None:
            self.__route_data = None

        _route_data = []
        for route_entry in newvalue:
            dest = route_entry[0]
            prefix = route_entry[1]
            next_hop = None
            metric = None

            try:
                next_hop = route_entry[2]
            except IndexError:
                pass

            try:
                metric = route_entry[3]
            except IndexError:
                pass

            new_entry = dbus.Dictionary({
                "dest": dest,
                "prefix": prefix
            }, signature=dbus.Signature("sv"))

            if next_hop:
                new_entry["next-hop"] = next_hop

            if metric:
                new_entry["metric"] = metric

            _route_data.append(new_entry)

        self.__route_data = dbus.Array(_route_data, signature=dbus.Signature("a{sv}"))


class DbusIpv4Settings(BaseDbusIpSettings):
    ip_version = 4


class DbusIpv6Settings(BaseDbusIpSettings):
    ip_version = 6
