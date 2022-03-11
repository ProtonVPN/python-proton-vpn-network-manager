class NetworkManagerBus:
    """
    NetworkManagerBus is a python bus that allows flexibility in communicating with
    NetworkManager via dbus.

    .. code-block::
        from proton.vpn.backend.linux.networkmanager.dbus import NetworkManagerBus
        nm_bus = NetworkManagerBus()
    """
    def __init__(self):
        import dbus
        self.__bus = dbus.SystemBus()

    def get_network_manager(self) -> "NetworkManagerObjectPath":
        """
            :return: dbus wrapper for `NetworkManager` object path
            :rtype: NetworkManagerObjectPath
        """
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import NetworkManagerObjectPath 
        return NetworkManagerObjectPath(self.__bus)

    def get_network_manager_settings(self) -> "NetworkManagerSettingsObjectPath":
        """
            :return: dbus wrapper for `NetworkManager/Settings` object path
            :rtype: NetworkManagerSettingsObjectPath
        """
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import NetworkManagerSettingsObjectPath 
        return NetworkManagerSettingsObjectPath(self.__bus)

    def get_device(self, object_path: str) -> "DeviceObjectPath":
        """
            :param object_path: the name of the object path. Usually the
                last element of an object path, preceded by the last `/`
            :type object_path: str
            :return: dbus wrapper for `NetworkManager/Devices/*` object path
            :rtype: DeviceObjectPath
        """
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import DeviceObjectPath 
        return DeviceObjectPath(self.__bus, str(object_path))

    def get_active_connection(self, object_path: str) -> "ActiveConnectionObjectPath":
        """
            :param object_path: the name of the object path. Usually the
                last element of an object path, preceded by the last `/`
            :type object_path: str
            :return: dbus wrapper for `NetworkManager/ActiveConnection/*` object path
            :rtype: ActiveConnectionObjectPath
        """
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import ActiveConnectionObjectPath 
        return ActiveConnectionObjectPath(self.__bus, str(object_path))

    def get_connection_settings(self, object_path: str) -> "ConnectionSettingsObjectPath":
        """
            :param object_path: the name of the object path. Usually the
                last element of an object path, preceded by the last `/`
            :type object_path: str
            :return: dbus wrapper for `NetworkManager/Settings/*` object path
            :rtype: ConnectionSettingsObjectPath
        """
        from proton.vpn.backend.linux.networkmanager.dbus.nm_object_path import ConnectionSettingsObjectPath 
        return ConnectionSettingsObjectPath(self.__bus, str(object_path))
