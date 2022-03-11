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
