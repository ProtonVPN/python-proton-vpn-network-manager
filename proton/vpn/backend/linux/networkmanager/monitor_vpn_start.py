from proton.vpn.backend.linux.networkmanager.dbus import NetworkManagerBus
from proton.vpn.backend.linux.networkmanager.enum import NMActiveConnectionState


class MonitorVPNConnectionStart:
    def __init__(self, uuid, callback):
        self.uuid = uuid
        self.nm_bus = NetworkManagerBus()
        self.vpn_check(callback)

    def vpn_check(self, callback):
        for active_conn in self.nm_bus.get_network_manager().active_connections:
            if active_conn.uuid == self.uuid:
                if active_conn.state == NMActiveConnectionState.ACTIVATING:
                    active_conn.connect_on_vpn_state_changed(callback)
                elif active_conn.state == NMActiveConnectionState.ACTIVATED:
                    print("Activated State")
                    # FIX-ME: Inform already connected
                    pass

                break
