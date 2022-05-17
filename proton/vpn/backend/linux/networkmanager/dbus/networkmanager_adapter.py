from .dbus_adapter import BaseDbusAdapter
import dbus.exceptions
from proton.vpn.backend.linux.networkmanager.dbus.exceptions import ProtonDbusException


class BaseNetworkManagerDbusAdapter(BaseDbusAdapter):
    """
    Base class from which all dbus object paths should derive from.

    All sub-classes should define their own `specific_object_path_prefix`
    and depending if the object path is stable or not, should also define
    `_object_path`.

    A stable objec path is one that does not change, ie `/org/freedesktop/NetworkManager`.
    An unstable object path is the done that exists at a given point but removed later,
    and vice-versa. For such cases it is reccomended to use pass only the last element of the
    object path to the constructor, so that the object path can be automatically built based on 
    `nm_object_path_prefix` and `specific_object_path_prefix`.

    Given that not all object paths have the same dbus interfaces (and the number of interfaces),
    not all sub-classes will necessarly have the exact same methods.

    To create a new object path, you need to know if it's a stable path or not.

    Example of stable paths:
        - `/org/freedesktop/NetworkManager/`
        - `/org/freedesktop/NetworkManager/AgentManager`
        - `/org/freedesktop/NetworkManager/DnsManager`
        - etc

    .. code-block::

        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import BaseNetworkManagerDbusAdapter

        class NetworkManagerAgentManagerObjectPath(BaseNetworkManagerDbusAdapter):
            specific_object_path_prefix = "AgentManager"
            _object_path = "/org/freedesktop/NetworkManager/" + specific_object_path_prefix
            example_interface = "org.freedesktop.NetworkManager.AgentManager"

            def _ensure_that_object_exists(self):
                return self.get_all_properties(self.example_interface)

        # To instantiate this class all you need to do is pass it a bus
        import dbus
        agent_manager = NetworkManagerAgentManagerObjectPath(dbus.SystemBus())

    Example of unstable paths:
        - /org/freedesktop/NetworkManager/Devices/*
        - /org/freedesktop/NetworkManager/ActiveConnection/*
        - /org/freedesktop/NetworkManager/Settings/*
        - etc

    .. code-block::

        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import BaseNetworkManagerDbusAdapter

        class NetworkManagerIP4ObjectPath(BaseNetworkManagerDbusAdapter):
            specific_object_path_prefix = "IP4Config/"
            _object_path = "/org/freedesktop/NetworkManager/" + specific_object_path_prefix
            example_interface = "org.freedesktop.NetworkManager.IP4Config"

            def _ensure_that_object_exists(self):
                return self.get_all_properties(self.example_interface)

        # To instantiate this class, you need to pass the bus but also the
        # name of the object, which in this case let it be 10
        import dbus
        ip4 = NetworkManagerIP4ObjectPath(dbus.SystemBus(), 10)
    """
    nm_object_path_prefix = "/org/freedesktop/NetworkManager/"
    bus_name = "org.freedesktop.NetworkManager"
    specific_object_path_prefix = ""

    def __init__(self, bus, object_path=None):
        self.bus = bus
        try:
            if not self._object_path:
                object_path = self.nm_object_path_prefix + self.specific_object_path_prefix + str(object_path)
        except AttributeError:
            object_path = self.nm_object_path_prefix + self.specific_object_path_prefix + str(object_path)

        super().__init__(self.bus, self.bus_name, object_path)


class NetworkManagerAdapter(BaseNetworkManagerDbusAdapter):
    """
    Provides an easy way to talk to `/org/freedesktop/NetworkManager` dbus object.

    .. code-block::
        import dbus
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import NetworkManagerAdapter

        nm = NetworkManagerAdapter(dbus.SystemBus())
    """
    specific_object_path_prefix = ""
    _object_path = "/org/freedesktop/NetworkManager" + specific_object_path_prefix
    nm_interface_path = "org.freedesktop.NetworkManager"

    @property
    def properties(self) -> "dict":
        """
            :return: properties
            :rtype: dict
        """
        return self.get_all_properties(self.nm_interface_path)

    @property
    def networkmanager_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.nm_interface_path)

    @property
    def active_connections(self) -> "Generator[ActiveConnectionAdapter]":
        """
            :return: next active connection
            :rtype: ActiveConnectionAdapter
        """
        for active_connection_object_path in self.get_property(self.nm_interface_path, "ActiveConnections"):
            try:
                yield ActiveConnectionAdapter(
                    self.bus,
                    active_connection_object_path.split("/")[-1]
                )
                continue
            except (RuntimeError, StopIteration):
                # When exiting a yielded for loop with `break` or `return`
                # an exception is raised. This exceptions has to be catched.
                continue

    def search_for_connection(self, uuid=None, interface_name=None) -> "ConnectionSettingsAdapter":
        """
            :param uuid: search based on uuid
            :type uuid: string
            :param interface_name: search based on virtual interface
            :type interface_name: string
            :return: connection settings of matching connection
            :rtype: ConnectionSettingsAdapter
            :raises: RuntimeError if both args or no args are passed

        Either `uuid` or `by_interface_name` has to be passed.
        """
        if not uuid and not interface_name or uuid and interface_name:
            raise RuntimeError("Only one of the args should be passed")

        active_connections = list(self.active_connections)
        all_connection_list = list(NetworkManagerSettingsAdapter(self.bus).stored_connections)
        all_connection_list.extend(active_connections)

        for connection in all_connection_list:
            # active_connections provide path to active connections ie:
            # /org/freedesktop/NetworkManager/ActiveConnection/*
            # but we're need a path to connection settings ie:
            # /org/freedesktop/NetworkManager/Settings/*

            try:
                connection = connection.connection_settings_adapter
            except AttributeError:
                pass
            except (dbus.exceptions.DBusException, RuntimeError):
                continue

            if (
                uuid and uuid == connection.uuid
            ) or (
                interface_name and (
                    interface_name == connection.vpn_virtual_device
                    or interface_name == connection.interface_name
                )
            ):
                return connection

        return ""

    @property
    def devices(self) -> "Generator[DeviceAdapter]":
        """
            :return: next device object
            :rtype: DeviceAdapter
        """
        for device_object_path in self.networkmanager_interface.GetAllDevices():
            yield DeviceAdapter(self.bus, device_object_path.split("/")[-1])

    def activate_connection(self, connection_settings_object_path, device_object_path, specific_object=None):
        """Activate existing connection.

            :param connection_settings_path: The connection to activate.
                If "/" is given, a valid device path must be given, and
                NetworkManager picks the best connection to activate for the
                given device. VPN connections must alwayspass a valid
                connection path.
            :type active_connection_object_path: str
            :param device_path: The object path of device to be activated
                for physical connections. This parameter is ignored for VPN
                connections, because the specific_object (if provided)
                specifies the device to use.
            :type device_path: str
            :param specific_object: Optional.
                The path of a connection-type-specific
                object this activation should use. This parameter is currently
                ignored for wired and mobile broadband connections, and the
                value of "/" should be used (ie, no specific object). For
                Wi-Fi connections, pass the object path of a specific AP from
                the card's scan list, or "/" to pick an AP automatically.
                For VPN connections, pass the object path of an
                ActiveConnection object that should serve as the "base"
                connection (to which the VPN connections lifetime
                will be tied), or pass "/" and NM will automatically use
                the current default device.
            :type specific_object: str

            :return: active connection
            :rtype: ActiveConnectionAdapter
        """
        connection_object_path = self.networkmanager_interface.ActivateConnection(
            connection_settings_object_path,
            device_object_path,
            specific_object if specific_object else "/"
        )

        if not connection_object_path:
            return None

        return ActiveConnectionAdapter(connection_object_path)

    def disconnect_connection(self, active_connection_object_path):
        """
            :param active_connection_object_path: object path to connection
            :type active_connection_object_path: str
        """
        self.networkmanager_interface.DeactivateConnection(active_connection_object_path)

    def _ensure_that_object_exists(self):
        self.properties

    def connect_on_device_added(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `DeviceAdded` signal is emitted

        Callback will return a object path of :type: str
        """
        self._connect_to_signal(
            self.nm_interface_path,
            "DeviceAdded",
            callback,
            **kwargs
        )

    def connect_on_device_removed(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `DeviceRemoved` signal is emitted

        Callback will return a object path of :type: str
        """
        self._connect_to_signal(
            self.nm_interface_path,
            "DeviceRemoved",
            callback,
            **kwargs
        )

    def connect_on_check_permissions(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `CheckPermissions` signal is emitted
        """
        self._connect_to_signal(
            self.nm_interface_path,
            "CheckPermissions",
            callback,
            **kwargs
        )

    def connect_on_state_changed(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                network `StateChanged` signal is emitted

        Callback will return the network state of :type: int
        """
        self._connect_to_signal(
            self.nm_interface_path,
            "StateChanged",
            callback,
            **kwargs
        )


class NetworkManagerSettingsAdapter(BaseNetworkManagerDbusAdapter):
    """
    Provides an easy way to talk to `/org/freedesktop/NetworkManager/Settings` dbus object.

    .. code-block::
        import dbus
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import NetworkManagerSettingsAdapter

        nm = NetworkManagerSettingsAdapter(dbus.SystemBus())
    """
    specific_object_path_prefix = "Settings"
    _object_path = "/org/freedesktop/NetworkManager/" + specific_object_path_prefix
    settings_interface_path = "org.freedesktop.NetworkManager.Settings"

    @property
    def properties(self) -> "dict":
        """
            :return: properties
            :rtype: dict
        """
        return self.get_all_properties(self.settings_interface_path)

    @property
    def settings_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.settings_interface_path)

    @property
    def stored_connections(self) -> "Generator[ConnectionSettingsAdapter]":
        """
            :return: next stored connection
            :rtype: ConnectionSettingsAdapter
        """
        for stored_connection_object_path in self.settings_interface.ListConnections():
            yield ConnectionSettingsAdapter(
                self.bus,
                stored_connection_object_path.split("/")[-1]
            )

    def reload_connections(self):
        self.settings_interface.ReloadConnections()

    def add_connection(self, connection: dict) -> "ConnectionSettingsAdapter":
        object_path = None
        try:
            object_path = self.settings_interface.AddConnection(connection)
        except dbus.exceptions.DBusException as e:
            raise ProtonDbusException(
                "Connection could not be created. Check NetworkManager syslogs"
            ) from e

        if not object_path:
            raise ProtonDbusException("Connection could not be created. Check NetworkManager syslogs")

        return ConnectionSettingsAdapter(self.bus, object_path.split("/")[-1])

    def _ensure_that_object_exists(self):
        self.properties

    def connect_on_connection_removed(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `ConnectionRemoved` signal is emitted

        Callback will return a object path of :type: str
        """
        self._connect_to_signal(
            self.settings_interface_path,
            "ConnectionRemoved",
            callback,
            **kwargs
        )

    def connect_on_new_connection(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `NewConnection` signal is emitted

        Callback will return a object path of :type: str
        """
        self._connect_to_signal(
            self.settings_interface_path,
            "NewConnection",
            callback,
            **kwargs
        )


class DeviceAdapter(BaseNetworkManagerDbusAdapter):
    """
    Provides an easy way to talk to `/org/freedesktop/NetworkManager/Devices/*` dbus objects.

    .. code-block::
        import dbus
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import DeviceAdapter

        device = "5"
        nm = DeviceAdapter(dbus.SystemBus(), device)
    """
    specific_object_path_prefix = "Devices/"

    device_interface_path = "org.freedesktop.NetworkManager.Device"
    device_generic_interface_path = "org.freedesktop.NetworkManager.Device.Generic"
    statistics_interface_path = "org.freedesktop.NetworkManager.Device.Statistics"
    wired_interface_path = "org.freedesktop.NetworkManager.Device.Wired"

    @property
    def device_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.device_interface_path)

    @property
    def device_generic_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.device_generic_interface_path)

    @property
    def statistics_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.statistics_interface_path)

    @property
    def wired_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.wired_interface_path)

    @property
    def available_connections(self) -> "Generator[ConnectionSettingsAdapter]":
        """
            :return: next available connection for this device
            :rtype: ConnectionSettingsAdapter
        """
        for connection_settings_object_path in self.get_property(self.device_generic_interface, "AvailableConnections"):
            yield ConnectionSettingsAdapter(self.bus, connection_settings_object_path.split("/")[-1])

    def does_connection_belong_to_this_device(self, connection_settings_path: str) -> "bool":
        """
            :param connection_settings_path: object path to connection settings
            :type connection_settings_path: str
            :return: if provided connection belongs to this device or not
            :rtype: bool
        """
        if len(list(self.available_connections)) < 1 or connection_settings_path not in [conn.object_path in self.available_connections]:
            return False

        return True

    def _ensure_that_object_exists(self):
        self.get_all_properties(self.device_interface_path)


class ActiveConnectionAdapter(BaseNetworkManagerDbusAdapter):
    """
    Provides an easy way to talk to `/org/freedesktop/NetworkManager/ActiveConnection/*` dbus objects.

    .. code-block::
        import dbus
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import ActiveConnectionAdapter

        active_connection = "99"
        nm = ActiveConnectionAdapter(dbus.SystemBus(), active_connection)
    """
    specific_object_path_prefix = "ActiveConnection/"

    active_connection_interface_path = "org.freedesktop.NetworkManager.Connection.Active"
    vpn_connection_interface_path = "org.freedesktop.NetworkManager.VPN.Connection"

    @property
    def properties(self) -> "dict":
        """
            :return: connection properties
            :rtype: dict
        """
        return self.get_all_properties(self.active_connection_interface_path)

    @property
    def vpn_properties(self) -> "dict":
        """
            :return: vpn properties
            :rtype: dict

        Since not all active connections are of type VPN, this will sometimes
        return empty.
        """
        if self.is_vpn:
            return self.get_all_properties(self.vpn_connection_interface_path)

        return []

    @property
    def connection_settings_adapter(self) -> "ConnectionSettingsAdapter":
        """
            :return: connection settings for this active connection
            :rtype: ConnectionSettingsAdapter
            :raises: RuntimeError if object does not exist/path is invalid
        """
        return ConnectionSettingsAdapter(
            self.bus,
            self.properties.get("Connection").split("/")[-1]
        )

    @property
    def uuid(self) -> "str":
        """
            :return: unique id of this connection
            :rtype: str
        """
        return self.properties.get("Uuid")

    @property
    def id(self) -> "str":
        """
            :return: human readeable id/name of this connection
            :rtype: str
        """
        return self.properties.get("Id")

    @property
    def devices(self) -> "Generator[DeviceAdapter]":
        """
            :return: next available connection for this device
            :rtype: DeviceAdapter
        """
        for device_object_path in self.properties.get("Devices"):
            yield DeviceAdapter(self.bus, device_object_path.split("/")[-1])

    @property
    def default_ipv4(self) -> "bool":
        """
            :return: if this is the default ipv4 connection
            :rtype: bool
        """
        return bool(self.properties.get("Default"))

    @property
    def ipv4config(self) -> "dict":
        """
            :return: ipv4 settings
            :rtype: dict
        """
        return self.properties.get("Ip4Config")

    @property
    def default_ipv6(self) -> "bool":
        """
            :return: if this is the default ipv6 connection
            :rtype: bool
        """
        return bool(self.properties.get("Default6"))

    @property
    def ipv6config(self) -> "dict":
        """
            :return: ipv6 settings
            :rtype: dict
        """
        return self.properties.get("Ip6Config")

    @property
    def state(self) -> "NMActiveConnectionState":
        """
            :return: the current state of this connection
            :rtype: NMActiveConnectionState
        """
        from proton.vpn.backend.linux.networkmanager.enum import NMActiveConnectionState
        return NMActiveConnectionState(int(self.properties.get("State")))

    @property
    def is_vpn(self) -> "bool":
        """
            :return: if this active connection is of type vpn
            :rtype: bool
        """
        if self.properties.get("Type") == "vpn" or self.properties.get("Type") == "wireguard":
            return True

        return False

    @property
    def active_connection_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return self._get_interface_from_path(self.active_connection_interface_path)

    def connect_on_vpn_state_changed(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                vpn connection `VpnStateChanged` signal is emitted

        Callback will return a two args of :type: int
        """
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "VpnStateChanged",
            callback,
            **kwargs
        )

    def connect_on_state_changed(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                connection `StateChanged` signal is emitted

        Callback will return a two args of :type: int
        """
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "StateChanged",
            callback,
            **kwargs
        )

    def _ensure_that_object_exists(self):
        self.properties


class ConnectionSettingsAdapter(BaseNetworkManagerDbusAdapter):
    """
    Provides an easy way to talk to `/org/freedesktop/NetworkManager/Settings/*` dbus objects.

    .. code-block::
        import dbus
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import ConnectionSettingsAdapter

        connection_settings = "131"
        nm = ConnectionSettingsAdapter(dbus.SystemBus(), connection_settings)
    """
    specific_object_path_prefix = "Settings/"
    connection_settings_interface_path = "org.freedesktop.NetworkManager.Settings.Connection"

    @property
    def properties(self) -> "dict":
        """
            :return: connection properties
            :rtype: dict
        """
        return self.get_all_properties(self.connection_settings_interface_path)

    @property
    def uuid(self) -> "str":
        """
            :return: unique id of this connection
            :rtype: str
        """
        return self.connection_settings.get("uuid")

    @property
    def id(self) -> "str":
        """
            :return: human readeable id/name of this connection
            :rtype: str
        """
        return self.connection_settings.get("id")

    @property
    def is_vpn(self) -> "bool":
        """
            :return: if this active connection is of type vpn
            :rtype: bool
        """
        if self.connection_settings.get("type") == "vpn" or self.connection_settings.get("type") == "wireguard":
            return True

        return False

    @property
    def interface_name(self):
        return self.connection_settings.get("interface-name")

    @property
    def vpn_virtual_device(self) -> "str":
        """
            :return: the virtual device of a vpn connection
            :rtype: str
        """
        if not self.is_vpn or "dev" not in self.vpn_settings.get("data", {}):
            return ""

        return self.vpn_settings.get("data")["dev"]

    def delete_connection(self) -> None:
        """Delete this connection"""
        try:
            self.connection_settings_interface.Delete()
        except dbus.exceptions.DBusException() as e:
            raise ProtonDbusException(
                "Unable to delete connection {}. "
                "See NetworkManager syslogs".format(self)
            ) from e

    def update_settings(self, properties: "dbus.Dictionary"):
        """
            :param properties: dbus dictionary with all the properties
                in expected format.
            :type properties: dbus.Dictionary
        """
        try:
            self.connection_settings_interface.Update(properties)
        except dbus.exceptions.DBusException() as e:
            raise ProtonDbusException(
                "Unable to update connection {}. "
                "See NetworkManager syslogs".format(self)
            ) from e

    @property
    def connection_settings(self) -> "dict":
        """
            :return: connection settings
            :rtype: dict
        """
        return self.__settings.get("connection", {})

    @property
    def vpn_settings(self) -> "dict":
        """
            :return: ipv4 settings
            :rtype: dict

        Since not all connections have vpn settings, this
        will return an empty dict if there is none.
        """
        return self.__settings.get("vpn", {})

    @property
    def ipv4_settings(self) -> "dict":
        """
            :return: ipv4 settings
            :rtype: dict
        """
        return self.__settings.get("ipv4", {})

    @property
    def ipv6_settings(self) -> "dict":
        """
            :return: ipv6 settings
            :rtype: dict
        """
        return self.__settings.get("ipv6", {})

    @property
    def proxy_settings(self) -> "dict":
        """
            :return: proxy settings
            :rtype: dict
        """
        return self.__settings.get("proxy", {})

    @property
    def __settings(self) -> "dict":
        """
            :return: connection settings
            :rtype: dict
        """
        try:
            return self.connection_settings_interface.GetSettings()
        except dbus.exceptions.DBusException:
            return {}

    def connect_on_removed(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `Removed` signal is emitted
        """
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "Removed",
            callback,
            **kwargs
        )

    def connect_on_updated(self, callback, **kwargs):
        """
            :param callback: callback to receive when
                `Updated` signal is emitted
        """
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "Updated",
            callback,
            **kwargs
        )

    @property
    def connection_settings_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface
            :rtype: dbus.proxies.Interface

        Use this property to call any methods under this specific interface.
        """
        return self._get_interface_from_path(self.connection_settings_interface_path)

    def _ensure_that_object_exists(self):
        self.properties
