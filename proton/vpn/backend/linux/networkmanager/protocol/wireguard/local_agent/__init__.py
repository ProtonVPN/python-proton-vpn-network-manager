"""
Local Agent module.


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
from proton.vpn import logging

logger = logging.getLogger(__name__)


try:
    from .external_local_agent import (
        AgentConnector, AgentConnection, Status,
        State, Reason, ReasonCode, AgentFeatures,
        LocalAgentError, ExpiredCertificateError, ErrorMessage
    )
except ModuleNotFoundError:
    from .fallback_local_agent import (
        AgentConnector, AgentConnection, Status,
        State, Reason, ReasonCode, AgentFeatures,
        LocalAgentError, ExpiredCertificateError, ErrorMessage
    )
    logger.info("Fallback local agent was loaded.")

__all__ = [
    "AgentConnector", "AgentConnection", "Status",
    "State", "Reason", "ReasonCode", "AgentFeatures",
    "LocalAgentError", "ExpiredCertificateError", "ErrorMessage"
]
