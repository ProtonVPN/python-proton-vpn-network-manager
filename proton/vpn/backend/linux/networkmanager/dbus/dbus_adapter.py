import dbus
from abc import abstractmethod


class BaseDbusAdapter:
    """
    Base class that should be derived  to create additional python objects for
    easy dbus communication.

    Sub-classes should define _object_path either as class properties or they
    can be passed to the constructor, to dynamically create python objects
    based on provided object path. This is especially usefull if there are
    object paths that can be added or removed, and their path is not stable.

    It is also recommended that each sub-class implements a way so that
    not the entire object path is needed to be passed, but rather only the last
    element of the path. Looking at the BaseNetworkManagerDbusAdapter code:

    .. code-block::

        class BaseNetworkManagerDbusAdapter(BaseDbusAdapter):
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
s
        # `nm_object_path_prefix` is the base path of a dbus object,
        # which will be common for all objects whithin a bus.

        #`specific_object_path_prefix` is often the specific prefix for that object path. Looking at the
        # NetworkManager bus we can see:

        org/freedesktop/NetworkManager/ActiveConnection/5

        # where:
        # `org/freedesktop/NetworkManager/` == `nm_object_path_prefix`
        # `ActiveConnection/` == `specific_object_path_prefix`

    It is done this way so that next time I want to grab an
    active connection `5`, I just need to pass the number
    since the path will be automatically built.
    """
    properties_interface_path = "org.freedesktop.DBus.Properties"
    peer_interface_path = "org.freedesktop.DBus.Peer"
    introspectable_interface_path = "org.freedesktop.DBus.Introspectable"

    def __init__(self, bus: "dbus._dbus.SystemBus", bus_name: str, object_path: str = None):
        self.__bus = bus
        self.__bus_name = bus_name
        if object_path:
            self._object_path = object_path

        self.__cached_proxy_object = None

        try:
            self._ensure_that_object_exists()
        except Exception as e:
            raise RuntimeError("Invalid object path {}\n{}".format(self._object_path, e))

    def __repr__(self) -> str:
        return "{} <\"{}\">".format(str(self.__class__.__name__), self.object_path)

    @property
    def object_path(self) -> "str":
        """
            :return: dbus object path
            :rtype: str
        """
        return self._object_path

    @property
    def name(self) -> "str":
        """
            :return: name of the object
            :rtype: str

        Usually the name of an object path is preceded by the last `/`
        within an object path string.
        Since it can be cumbersone to always be splitting the string,
        a property was created for that purpose.
        """
        return str(self.object_path.split("/")[-1])

    @property
    def introspectable_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface to org.freedesktop.DBus.Introspectable
            :rtype: dbus.proxies.Interface

        Most of desktop dbus services provide an introspectable interface,
        although other 3rd party services might not have these.
        """
        return self._get_interface_from_path(self.introspectable_interface_path)

    @property
    def peer_interface(self) -> "dbus.proxies.Interface":
        """
            :return: proxy interface to org.freedesktop.DBus.Peer
            :rtype: dbus.proxies.Interface

        Most of desktop dbus services provide a peer interface,
        although other 3rd party services might not have these.
        """
        return self._get_interface_from_path(self.peer_interface_path)

    def connect_on_properties_changed(self, callback):
        """
            :param callback: callback to receive when signal is emitted
            :type callback: callable

        Subscribe to events when any of the properties of `self.object_path`
        are updated.
        """
        self._connect_to_signal(
            self.properties_interface_path,
            "PropertiesChanged",
            callback
        )

    def get_property(self, interface: str, property: str) -> "object":
        """
            :param interface: dbus interface name
            :type interface: str
            :param property_name: property name to get
            :type property_name: str
            :return: the value of the property, can be a list, dict or string
            :rtype: object
        """
        properties_interface = self._get_interface_from_path(self.properties_interface_path)

        return properties_interface.Get(interface, property)

    def get_all_properties(self, interface: str) -> "dict":
        """
            :param interface: dbus interface name
            :type interface: str
            :return: the value of the property,
                can be a list (dict within list)), dict or string
            :rtype: object
        """
        properties_interface = self._get_interface_from_path(self.properties_interface_path)

        return properties_interface.GetAll(interface)

    def set_property(self, interface: str, property: str, new_value: object) -> "None":
        """
            :param interface: dbus interface name
            :type interface: str
            :param property_name: property name to get
            :type property_name: str
            :type new_value: the new value for the given proprty.
                can be a list (dict within list)), dict or string
            :rtype: object
        """
        properties_interface = self._get_interface_from_path(self.properties_interface_path)
        properties_interface.Set(interface, property, new_value)

    def _connect_to_signal(self, interface, signal_name, callback, **kwargs):
        """
            :param interface: dbus interface name
            :type interface: str
            :param signal_name: name of the signal.
                Pay special attention upper/lowecase letters.
            :type signal_name: str
            :param callback: callback to receive when signal is emitted
            :type callback: callable

        Listen to dbus `signal_name`, of a given `interface` and receive
        updates to the spcified `callback`.
        """
        # https://dbus.freedesktop.org/doc/dbus-python/tutorial.html#getting-more-information-from-a-signal
        interface_obj = self._get_interface_from_path(interface)
        interface_obj.connect_to_signal(
            signal_name=signal_name,
            handler_function=callback,
            **kwargs
        )

    def _get_interface_from_path(self, interface_name: str) -> "dbus.proxies.Interface":
        """
        Gets the proxy object of the spcified interface name.
        Only classes deriving from this one should call method.

            :param interface: dbus interface name
            :type interface: str
            :return: proxy interface
            :rtype: dbus.proxies.Interface
        """
        return dbus.Interface(self.__proxy_object, interface_name)

    @property
    def __proxy_object(self) -> "dbus.proxies.ProxyObject":
        """
        Gets the proxy object of the spcified interface name, based on object path.

            :return: proxy object
            :rtype: dbus.proxies.ProxyObject
        """
        # https://dbus.freedesktop.org/doc/dbus-python/tutorial.html#receiving-signals-from-a-proxy-object
        if not self.__cached_proxy_object:
            self.__cached_proxy_object = self.__bus.get_object(
                self.__bus_name,
                self._object_path
            )

        return self.__cached_proxy_object

    @abstractmethod
    def _ensure_that_object_exists():
        """
        Abstract method that ensure that the object exists at creation time.

        It's up to developper on how to implement this, but it is reccomended
        to simply make a call to get_all_proprties() of an interface that
        your object path has, ie:

        .. code-block::
            def _ensure_that_object_exists():
                self.get_all_properties(self.some_interface_within_this_object_path)

        Doing this will always ensure that if the properties are not able to be fetched,
        then it's most probable that the object path is not existent.
        """
        raise NotImplementedError
