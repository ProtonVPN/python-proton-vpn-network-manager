from enum import Enum


class VPNConnectionStateEnum(Enum):
    """
    NMVpnConnectionState(int)

    0 (UNKNOWN): The state of the VPN connection is unknown.
    1 (PREPARING_TO_CONNECT): The VPN connection is preparing to connect.
    2 (NEEDS_CREDENTIALS): The VPN connection needs authorization credentials.
    3 (BEING_ESTABLISHED): The VPN connection is being established.
    4 (GETTING_IP_ADDRESS): The VPN connection is getting an IP address.
    5 (IS_ACTIVE): The VPN connection is active.
    6 (FAILED): The VPN connection failed.
    7 (DISCONNECTED): The VPN connection is disconnected.
    999 (UNKNOWN_ERROR): Custom error since NM can sometimes answer with no State
    """
    UNKNOWN = 0
    PREPARING_TO_CONNECT = 1
    NEEDS_CREDENTIALS = 2
    BEING_ESTABLISHED = 3
    GETTING_IP_ADDRESS = 4
    IS_ACTIVE = 5
    FAILED = 6
    DISCONNECTED = 7
    UNKNOWN_ERROR = 999


class VPNConnectionReasonEnum(Enum):
    """
    NMActiveConnectionStateReason(int)

    0 (UNKNOWN):  The reason for the active connection state change
            is unknown.
    1 (NOT_PROVIDED):  No reason was given for the
        active connection state change.
    2 (USER_HAS_DISCONNECTED):  The active connection changed state because
        the user disconnected it.
    3 (DEVICE_WAS_DISCONNECTED):  The active connection changed state because
        the device it was using was disconnected.
    4 (SERVICE_PROVIDER_WAS_STOPPED):  The service providing the
        VPN connection was stopped.
    5 (IP_CONFIG_WAS_INVALID):  The IP config of the active
        connection was invalid.
    6 (CONN_ATTEMPT_TO_SERVICE_TIMED_OUT):  The connection attempt
        to the VPN service timed out.
    7 (TIMEOUT_WHILE_STARTING_VPN_SERVICE_PROVIDER):  A timeout occurred while
        starting the service providing the VPN connection.
    8 (START_SERVICE_VPN_CONN_SERVICE_FAILED):  Starting the service
        providing the VPN connection failed.
    9 (SECRETS_WERE_NOT_PROVIDED):  Necessary secrets for the connection
        were not provided.
    10 (SERVER_AUTH_FAILED): Authentication to the server failed.
    11 (DELETED_FROM_SETTINGS): The connection was deleted from settings.
    12 (MASTER_CONN_FAILED_TO_ACTIVATE): Master connection of this
        connection failed to activate.
    13 (CREATE_SOFTWARE_DEVICE_LINK_FAILED): Could not create
        the software device link.
    14 (VPN_DEVICE_DISAPPEARED): The device this connection
        depended on disappeared.
    999 (UNKNOWN_ERROR): Custom error since NM can sometimes answer with no Reason
    """
    UNKNOWN = 0
    NOT_PROVIDED = 1
    USER_HAS_DISCONNECTED = 2
    DEVICE_WAS_DISCONNECTED = 3
    SERVICE_PROVIDER_WAS_STOPPED = 4
    IP_CONFIG_WAS_INVALID = 5
    CONN_ATTEMPT_TO_SERVICE_TIMED_OUT = 6
    TIMEOUT_WHILE_STARTING_VPN_SERVICE_PROVIDER = 7
    START_SERVICE_VPN_CONN_SERVICE_FAILED = 8
    SECRETS_WERE_NOT_PROVIDED = 9
    SERVER_AUTH_FAILED = 10
    DELETED_FROM_SETTINGS = 11
    MASTER_CONN_FAILED_TO_ACTIVATE = 12
    CREATE_SOFTWARE_DEVICE_LINK_FAILED = 13
    VPN_DEVICE_DISAPPEARED = 14
    UNKNOWN_ERROR = 999
