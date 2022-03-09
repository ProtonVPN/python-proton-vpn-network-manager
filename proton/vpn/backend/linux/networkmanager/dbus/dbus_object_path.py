import dbus
from abc import abstractmethod


class DbusObjectPath:
    properties_interface_path = "org.freedesktop.DBus.Properties"
    peer_interface_path = "org.freedesktop.DBus.Peer"
    introspectable_interface_path = "org.freedesktop.DBus.Introspectable"

    def __init__(self, bus, bus_name, object_path=None):
        self.__bus = bus
        self.__bus_name = bus_name
        if object_path:
            self._object_path = object_path

        self.__cached_proxy_object = None

        try:
            self._ensure_that_object_exists()
        except Exception as e:
            raise RuntimeError("Invalid object path {}\n{}".format(self._object_path, e))

    def __repr__(self):
        return "{} <\"{}\">".format(str(self.__class__.__name__), self.object_path)

    @property
    def object_path(self):
        return self._object_path

    @property
    def introspectable_interface(self):
        return self._get_interface_from_path(self.introspectable_interface_path)

    @property
    def peer_interface(self):
        return self._get_interface_from_path(self.peer_interface_path)

    def connect_on_properties_changed(self):
        self._connect_to_signal(
            self.properties_interface_path,
            "PropertiesChanged",
            self.on_properties_changed
        )

    def on_properties_changed(self, *args, **kwargs):
        pass

    def get_property(self, interface_name: str, property_name: str) -> object:
        properties_interface = self._get_interface_from_path(self.properties_interface_path)

        return properties_interface.Get(interface_name, property_name)

    def get_all_properties(self, interface_name: str) -> dict:
        properties_interface = self._get_interface_from_path(self.properties_interface_path)

        return properties_interface.GetAll(interface_name)

    def set_property(self, interface_name: str, property_name: str, new_property_value):
        properties_interface = self._get_interface_from_path(self.properties_interface_path)

        properties_interface.Set(interface_name, property_name, new_property_value)

    def _connect_to_signal(self, interface, signal_name, callback):
        interface.connect_to_signal(signal_name, method)

    def _get_interface_from_path(self, interface_name: str) -> "dbus.proxies.Interface":
        """Get interface of proxy object.

        Args:
            proxy_object (dbus.proxies.ProxyObject)
            interface_name (string): interface name/path

        Returns:
            dbus.proxies.Interface: properties interface
        """
        return dbus.Interface(self.__proxy_object, interface_name)

    @property
    def __proxy_object(self):
        if not self.__cached_proxy_object:
            self.__cached_proxy_object = self.__bus.get_object(
                self.__bus_name,
                self._object_path
            )

        return self.__cached_proxy_object

    @abstractmethod
    def _ensure_that_object_exists():
        raise NotImplementedError
