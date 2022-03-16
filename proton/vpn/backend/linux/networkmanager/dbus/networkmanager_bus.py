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

    def get_network_manager(self) -> "NetworkManagerAdapter":
        """
            :return: dbus wrapper for `NetworkManager` object path
            :rtype: NetworkManagerAdapter
        """
        from proton.vpn.backend.linux.networkmanager.dbus.networkmanager_adapter import NetworkManagerAdapter
        return NetworkManagerAdapter(self.__bus)

    def get_network_manager_settings(self) -> "NetworkManagerSettingsAdapter":
        """
            :return: dbus wrapper for `NetworkManager/Settings` object path
            :rtype: NetworkManagerSettingsAdapter
        """
        from proton.vpn.backend.linux.networkmanager.dbus.networkmanager_adapter import NetworkManagerSettingsAdapter
        return NetworkManagerSettingsAdapter(self.__bus)

    def get_device(self, object_path: str) -> "DeviceAdapter":
        """
            :param object_path: the name of the object path. Usually the
                last element of an object path, preceded by the last `/`
            :type object_path: str
            :return: dbus wrapper for `NetworkManager/Devices/*` object path
            :rtype: DeviceAdapter
        """
        from proton.vpn.backend.linux.networkmanager.dbus.networkmanager_adapter import DeviceAdapter
        return DeviceAdapter(self.__bus, str(object_path))

    def get_active_connection(self, object_path: str) -> "ActiveConnectionAdapter":
        """
            :param object_path: the name of the object path. Usually the
                last element of an object path, preceded by the last `/`
            :type object_path: str
            :return: dbus wrapper for `NetworkManager/ActiveConnection/*` object path
            :rtype: ActiveConnectionAdapter
        """
        from proton.vpn.backend.linux.networkmanager.dbus.networkmanager_adapter import ActiveConnectionAdapter
        return ActiveConnectionAdapter(self.__bus, str(object_path))

    def get_connection_settings(self, object_path: str) -> "ConnectionSettingsAdapter":
        """
            :param object_path: the name of the object path. Usually the
                last element of an object path, preceded by the last `/`
            :type object_path: str
            :return: dbus wrapper for `NetworkManager/Settings/*` object path
            :rtype: ConnectionSettingsAdapter
        """
        from proton.vpn.backend.linux.networkmanager.dbus.networkmanager_adapter import ConnectionSettingsAdapter
        return ConnectionSettingsAdapter(self.__bus, str(object_path))
