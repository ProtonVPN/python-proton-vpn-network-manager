from .nm_object_path import (ActiveConnectionObjectPath,
                             ConnectionSettingsObjectPath, DeviceObjectPath,
                             NetworkManagerObjectPath,
                             NetworkManagerSettingsObjectPath)


class NetworkManagerBus:
    def __init__(self):
        import dbus
        self.__bus = dbus.SystemBus()

    def get_network_manager(self) -> "NetworkManagerObjectPath":
        return NetworkManagerObjectPath(self.__bus)

    def get_network_manager_settings(self) -> "NetworkManagerSettingsObjectPath":
        return NetworkManagerSettingsObjectPath(self.__bus)

    def get_device(self, object_path: str) -> "DeviceObjectPath":
        return DeviceObjectPath(self.__bus, str(object_path))

    def get_active_connection(self, object_path: str) -> "ActiveConnectionObjectPath":
        return ActiveConnectionObjectPath(self.__bus, str(object_path))

    def get_connection_settings(self, object_path: str) -> "ConnectionSettingsObjectPath":
        return ConnectionSettingsObjectPath(self.__bus, str(object_path))

    def search_for_connection(self, by_uuid=False, by_interface_name=False) -> str:
        """Search for specified connection.

        Args:
            by_uuid (string): unique id 
            by_interface_name (string): Interface name.
        Returns:
           Connection settings path
        """
        if not by_uuid and not by_interface_name or by_uuid and by_interface_name:
            raise RuntimeError("Only one of the args should be passed")

        active_connections = self.get_network_manager().active_connections
        all_connection_list = self.get_network_manager_settings().stored_connections
        all_connection_list.extend(active_connections)

        for conn_settings_object_path in all_connection_list:
            try:
                conn_settings_object_path = self.get_active_connection(
                    conn_settings_object_path.split("/")[-1]
                ).connection_settings_object_path
            except RuntimeError as e:
                if "org.freedesktop.DBus.Error.UnknownMethod" in str(e):
                    pass

            conn_settings = self.get_connection_settings(conn_settings_object_path.split("/")[-1])
            if (
                by_uuid and by_uuid == conn_settings.connection_uuid
            ) or (
                by_interface_name and by_interface_name == conn_settings.vpn_virtual_device
            ):
                return conn_settings_object_path

        return None

    def activate_connection(self, connection_settings_path, device_path, specific_object=None):
        return self.get_network_manager().activate_connection(connection_settings_object_path, device_object_path)

    def disconnect_connection(self, connection_path):
        self.get_network_manager().disconnect_connection(connection_path)

    def delete_connection(self, connection_settings_path):
        self.get_connection_settings_object_path(connection_settings_path).delete_connection()
