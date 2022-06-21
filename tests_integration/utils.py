from typing import List, Dict

from proton.session import Session


def get_authenticated_session(proton_username: str, proton_password: str):
    """Given a username/password, it returns the authenticated Session object."""
    s = Session()
    assert s.authenticate(proton_username, proton_password)
    return s


def get_openvpn_username_and_password(authenticated_session: Session) -> (str, str):
    """Given an authenticated session, it returns the openvpn username and password."""
    response = authenticated_session.api_request("/vpn")
    assert response["Code"] == 1000
    openvpn_username = response["VPN"]["Name"]
    openvpn_password = response["VPN"]["Password"]

    return openvpn_username, openvpn_password


def get_vpn_server_list() -> List[Dict]:
    response = Session().api_request("/vpn/logicals")
    assert response["Code"] == 1000
    return response["LogicalServers"]


def get_vpn_server_by_name(server_name: str) -> Dict:
    return next((server for server in get_vpn_server_list() if server["Name"] == server_name))


def get_vpn_client_config() -> dict:
    response = Session().api_request("/vpn/clientconfig")
    assert response["Code"] == 1000
    return response
