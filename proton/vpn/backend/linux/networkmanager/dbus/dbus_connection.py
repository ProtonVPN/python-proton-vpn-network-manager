import dbus

__all__ = ["DbusConnection"]


class DbusConnection:
    def __init__(self):
        self.__connection_settings = DbusConnectionSettings(
            "human_readable_id", "interface_name"
        )
        self.__ipv4_settings = DbusIpv4Settings()
        self.__ipv6_settings = DbusIpv6Settings()

    def generate_configuration(self):
        conn_dict = dbus.Dictionary({
            'connection': self.__connection_settings.generate_configuration(),
            'ipv4': self.__ipv4_settings.generate_configuration(),
            'ipv6': self.__ipv6_settings.generate_configuration()
        })

        return conn_dict

    @property
    def settings(self) -> "DbusConnectionSettings":
        return self.__connection_settings

    @property
    def ipv4(self) -> "DbusIpv4Settings":
        return self.__ipv4_settings

    @property
    def ipv6(self) -> "DbusIpv6Settings":
        return self.__ipv6_settings


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
        settings = dbus.Dictionary({"type": self.__connection_type})

        if self.unique_id:
            settings["uuid"] = self.unique_id

        if self.human_readable_id:
            settings["id"] = self.human_readable_id

        if self.interface_name:
            settings["interface-name"] = self.interface_name

        return settings

    @property
    def connection_type(self) -> str:
        return self.__connection_type

    @connection_type.setter
    def connection_type(self, newvalue: str):
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


class BaseDbusIpSettings:
    ip_version = None

    def __init__(self):
        if not self.ip_version:
            raise RuntimeError("IP version not set")

        self.__address_data = None
        self.__method = None
        self.__dns = None
        self.__dns_priority = None
        self.__gateway = None
        self.__ignore_auto_dns = None
        self.__route_metric = None
        self.__addresses = None

    def generate_configuration(self):
        settings = dbus.Dictionary({})

        if self.address_data:
            settings["address-data"] = self.address_data

        if self.method:
            settings["method"] = self.method

        if self.dns_priority:
            settings["dns-priority"] = self.dns_priority

        if self.gateway:
            settings["gateway"] = self.gateway

        if self.ignore_auto_dns:
            settings["ignore-auto-dns"] = self.ignore_auto_dns

        if self.route_metric:
            settings["route-metric"] = self.route_metric

        if self.addresses:
            settings["addresses"] = self.addresses

        if self.dns:
            settings["dns"] = self.dns

        if len(settings) == 0:
            if self.ip_version == 4:
                raise RuntimeError("IPv4 must be defined")

            settings["method"] = "ignore"

        return settings

    @staticmethod
    def ipv4_to_int(ipv4_addr):
        import ipaddress
        return int.from_bytes(ipaddress.ip_address(ipv4_addr).packed, 'big')

    @staticmethod
    def ipv6_to_byte_list(ipv6_addr):
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
        assert newvalue.get("address")
        assert newvalue.get("prefix")  

        self.__address_data = dbus.Array([dbus.Dictionary(newvalue)], signature=dbus.Signature("a{sv}"))

    @property
    def method(self) -> str:
        return self.__method

    @method.setter
    def method(self, newvalue: str):
        self.__method = newvalue

    @property
    def dns(self) -> int:
        return self.__dns

    @dns.setter
    def dns(self, newvalue: list):
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
        self.__dns_priority = int(newvalue)

    @property
    def gateway(self) -> str:
        return self.__gateway

    @gateway.setter
    def gateway(self, newvalue: str):
        self.__gateway = str(newvalue)

    @property
    def ignore_auto_dns(self) -> bool:
        return self.__ignore_auto_dns

    @ignore_auto_dns.setter
    def ignore_auto_dns(self, newvalue: bool):
        self.__ignore_auto_dns = bool(newvalue)

    @property
    def route_metric(self) -> int:
        return self.__route_metric

    @route_metric.setter
    def route_metric(self, newvalue: int):
        self.__route_metric = int(newvalue)

    @property
    def addresses(self) -> dict:
        return self.__addresses

    @addresses.setter
    def addresses(self, newvalue: list):
        """
        For ipv6 addressess has to be a dbus.Struct with signature (ayuay),
        where the:
            start `ay`: the server ipv6 transformed to byte (u8 list)
            middle `u`: the CIDR (/8, /16, /32, etc)
            end `ay`: same as at the start but instead of server I\P here is the gateway IP
        Here's a suggestion on how to build:

        addresses_ipv6 = dbus.Struct(
            (
                [ dbus.Byte(n) for n in list(ipaddress.ip_address(ipv6_addr).packed) ],
                dbus.UInt32(64),
                [ dbus.Byte(n) for n in list(ipaddress.ip_address(ipv6_addr).packed) ]
            )
        ---------------------------------------------------------------------------------------
        For ipv4 is much simplier but the structure is the same. Instead of a struct an
        array is used instead to store first the server IP, then the CIDR and lastly the
        gateway IP. Here is an example:

        ipv4_addresses = dbus.Array(
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


class DbusIpv4Settings(BaseDbusIpSettings):
    ip_version = 4


class DbusIpv6Settings(BaseDbusIpSettings):
    ip_version = 6