"""
Local Agent module that uses Proton external local agent implementation.


Copyright (c) 2024 Proton AG

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
import proton.vpn.local_agent  # pylint: disable=import-error, no-name-in-module
from proton.vpn.local_agent import (  # pylint: disable=no-name-in-module, import-error
    AgentConnection, Status, State, Reason, ReasonCode,
    AgentFeatures, LocalAgentError, ExpiredCertificateError, ErrorMessage
)
from proton.vpn.session.exceptions import VPNCertificateExpiredError


class AgentConnector:  # pylint: disable=too-few-public-methods
    """AgentConnector that wraps Proton external local agent implementation."""
    async def connect(self, vpn_server_domain: str, credentials) -> AgentConnection:
        """Connect to the local agent server."""
        try:
            certificate = credentials.certificate_pem
        except VPNCertificateExpiredError as exc:
            raise ExpiredCertificateError("Certificate expired") from exc

        return await proton.vpn.local_agent.AgentConnector().connect(  # pylint: disable=E1101
            vpn_server_domain,
            credentials.get_ed25519_sk_pem(),
            certificate
        )


__all__ = [
    "AgentConnector", "AgentConnection", "Status", "State", "Reason", "ReasonCode",
    "AgentFeatures", "ExpiredCertificateError", "LocalAgentError", "ErrorMessage"
]
