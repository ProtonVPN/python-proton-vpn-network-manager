from proton.vpn.backend.linux.networkmanager.dbus import NetworkManagerBus
from proton.vpn.backend.linux.networkmanager.enum import NMActiveConnectionState


class ConnectionMonitor:
    def __init__(self, uuid, callback, connection_set_down=False):
        self.uuid = uuid
        self.nm_bus = NetworkManagerBus()
        self.monitor(callback, connection_set_down)

    def monitor(self, callback, connection_set_down):
        if not connection_set_down:
            self.monitor_on_set_up(callback)
        else:
            self.monitor_on_set_down(callback)

    def monitor_on_set_up(self, callback):
        for active_conn in self.nm_bus.get_network_manager().active_connections:
            if active_conn.uuid == self.uuid:
                if active_conn.state == NMActiveConnectionState.ACTIVATING:
                    active_conn.connect_on_vpn_state_changed(callback)
                elif active_conn.state == NMActiveConnectionState.ACTIVATED:
                    callback(5, 0)
                break

    def monitor_on_set_down(self, callback):
        conn = self.nm_bus.get_network_manager().search_for_connection(self.uuid)
        if conn:
            self.__to_be_removed_object_path = conn.object_path
            self.__callback = callback
            self.nm_bus.get_network_manager_settings().connect_on_connection_removed(
                self._confirm_connection_has_been_removed,
            )
            conn.delete_connection()
        else:
            callback(None)

    def _confirm_connection_has_been_removed(self, removed_connection_object_path):
        if self.__to_be_removed_object_path == removed_connection_object_path:
            self.__callback(True)
        else:
            self.__callback(False)
