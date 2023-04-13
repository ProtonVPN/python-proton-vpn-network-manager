"""
Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""
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
