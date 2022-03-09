from .dbus_object_path import DbusObjectPath


class NetworkManagerDbusObjectPath(DbusObjectPath):
    nm_object_path_prefix = "/org/freedesktop/NetworkManager/"
    bus_name = "org.freedesktop.NetworkManager"

    def __init__(self, bus, object_path=None):
        try:
            if not self._object_path:
                object_path = self.nm_object_path_prefix + self.specific_object_path_prefix + str(object_path)
        except AttributeError:
            object_path = self.nm_object_path_prefix + self.specific_object_path_prefix + str(object_path)

        super().__init__(bus, self.bus_name, object_path)


class NetworkManagerObjectPath(NetworkManagerDbusObjectPath):
    specific_object_path_prefix = ""
    _object_path = "/org/freedesktop/NetworkManager" + specific_object_path_prefix
    nm_interface_path = "org.freedesktop.NetworkManager"

    @property
    def properties(self):
        return self.get_all_properties(self.nm_interface_path)

    @property
    def networkmanager_interface(self):
        return self._get_interface_from_path(self.nm_interface_path)

    @property
    def active_connections(self):
        return self.get_property(self.nm_interface_path, "ActiveConnections")

    @property
    def devices(self):
        return self.networkmanager_interface.GetAllDevices()

    def activate_connection(self, connection_settings_object_path, device_object_path, specific_object=None):
        """Activate existing connection.

        Args:
            connection_settings_path (string): The connection to activate.
                If "/" is given, a valid device path must be given, and
                NetworkManager picks the best connection to activate for the
                given device. VPN connections must alwayspass a valid
                connection path.
            device_path (string): The object path of device to be activated
                for physical connections. This parameter is ignored for VPN
                connections, because the specific_object (if provided)
                specifies the device to use.
            specific_object (string): The path of a connection-type-specific
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

        Returns:
            string | None: either path to active connection
            if connection was successfully activated
            or None if not.
        """
        connection__object_path = self.networkmanager_interface.ActivateConnection(
            connection_settings_object_path,
            device_object_path,
            specific_object if specific_object else "/"
        )

        return connection_object_path

    def disconnect_connection(self, active_connection_object_path):
        self.networkmanager_interface.DeactivateConnection(active_connection_object_path)

    def _ensure_that_object_exists(self):
        self.properties


class NetworkManagerSettingsObjectPath(NetworkManagerDbusObjectPath):
    specific_object_path_prefix = "Settings"
    _object_path = "/org/freedesktop/NetworkManager/" + specific_object_path_prefix
    settings_interface_path = "org.freedesktop.NetworkManager.Settings"

    @property
    def properties(self):
        return self.get_all_properties(self.settings_interface_path)

    @property
    def settings_interface(self):
        return self._get_interface_from_path(self.settings_interface_path)

    @property
    def stored_connections(self):
        return self.settings_interface.ListConnections()

    def connect_on_check_permissions(self, callback) -> None:
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "CheckPermissions",
            callback
        )

    def connect_on_device_added(self, callback) -> str:
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "DeviceAdded",
            callback
        )

    def connect_on_device_removed(self, callback) -> str:
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "DeviceRemoved",
            callback
        )

    def connect_on_state_changed(self, callback) -> int:
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "DeviceRemoved",
            callback
        )

    def _ensure_that_object_exists(self):
        self.properties


class DeviceObjectPath(NetworkManagerDbusObjectPath):
    specific_object_path_prefix = "Devices/"

    device_interface_path = "org.freedesktop.NetworkManager.Device"
    device_generic_interface_path = "org.freedesktop.NetworkManager.Device.Generic"
    statistics_interface_path = "org.freedesktop.NetworkManager.Device.Statistics"
    wired_interface_path = "org.freedesktop.NetworkManager.Device.Wired"

    @property
    def device_interface(self):
        return self._get_interface_from_path(self.device_interface_path)

    @property
    def device_generic_interface(self):
        return self._get_interface_from_path(self.device_generic_interface_path)

    @property
    def statistics_interface(self):
        return self._get_interface_from_path(self.statistics_interface_path)

    @property
    def wired_interface(self):
        return self._get_interface_from_path(self.wired_interface_path)

    @property
    def available_connections(self):
        return self.get_property(self.device_generic_interface, "AvailableConnections")

    def does_connection_belong_to_this_device(self, connection_settings_path):
        if len(self.available_connections) < 1 or connection_settings_path not in self.available_connections:
            return False

        return True

    def _ensure_that_object_exists(self):
        self.get_all_properties(self.device_interface_path)


class ActiveConnectionObjectPath(NetworkManagerDbusObjectPath):
    specific_object_path_prefix = "ActiveConnection/"

    active_connection_interface_path = "org.freedesktop.NetworkManager.Connection.Active"
    vpn_connection_interface_path = "org.freedesktop.NetworkManager.VPN.Connection"

    @property
    def properties(self) -> dict:
        return self.get_all_properties(self.active_connection_interface_path)

    @property
    def vpn_properties(self) -> dict:
        return self.get_all_properties(self.vpn_connection_interface_path)

    @property
    def connection_settings_object_path(self):
        return self.properties.get("Connection")

    @property
    def uuid(self):
        return self.properties.get("Uuid")

    @property
    def id(self):
        return self.properties.get("Id")

    @property
    def devices(self):
        return self.properties.get("Devices")

    @property
    def default_ipv4(self):
        return self.properties.get("Default")

    @property
    def ipv4config(self):
        return self.properties.get("Ip4Config")

    @property
    def default_ipv6(self):
        return self.properties.get("Default6")

    @property
    def ipv6config(self):
        return self.properties.get("Ip6Config")

    @property
    def state(self):
        return self.properties.get("State")

    @property
    def is_vpn(self):
        # NMActiveConnectionState
        # State 1 = a network connection is being prepared
        # State 2 = there is a connection to the network
        if self.properties.get("Type") == "vpn" and self.state == 2:
            return True

        return False

    @property
    def active_connection_interface(self):
        return self._get_interface_from_path(self.active_connection_interface_path)

    def connect_on_vpn_state_changed(self, callback):
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "VPNStateChanged",
            callback
        )

    def connect_on_state_changed(self, callback):
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "StateChanged",
            callback
        )

    def _ensure_that_object_exists(self):
        self.properties


class ConnectionSettingsObjectPath(NetworkManagerDbusObjectPath):
    specific_object_path_prefix = "Settings/"
    connection_settings_interface_path = "org.freedesktop.NetworkManager.Settings.Connection"

    @property
    def properties(self):
        return self.get_all_properties(self.connection_settings_interface_path)

    @property
    def settings(self):
        return self.connection_settings_interface.GetSettings()

    @property
    def connection_settings_interface(self):
        return self._get_interface_from_path(self.connection_settings_interface_path)

    @property
    def uuid(self):
        return self.connection_settings.get("uuid")

    @property
    def id(self):
        return self.connection_settings.get("id")

    @property
    def is_vpn(self):
        if self.connection_settings.get("type") == "vpn":
            return True

        return False

    @property
    def vpn_virtual_device(self):
        if not self.is_vpn or "dev" not in self.vpn_settings.get("data", {}):
            return None

        return self.vpn_settings.get("data")["dev"]

    def delete_connection(self) -> None:
        self.connection_settings_interface.Delete()

    def connect_on_removed(self, callback):
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "Removed",
            callback
        )

    def connect_on_updated(self, callback):
        self._connect_to_signal(
            self.vpn_connection_interface_path,
            "Updated",
            callback
        )

    @property
    def connection_settings(self):
        return self.settings.get("connection", {})

    @property
    def vpn_settings(self):
        return self.settings.get("vpn", {})

    @property
    def ipv4_settings(self):
        return self.settings.get("ipv4", {})

    @property
    def ipv6_settings(self):
        return self.settings.get("ipv6", {})

    @property
    def proxy_settings(self):
        return self.settings.get("proxy", {})

    def _ensure_that_object_exists(self):
        self.properties
