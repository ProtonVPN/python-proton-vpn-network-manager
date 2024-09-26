"""
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
import asyncio
from typing import Optional, Awaitable

import proton.vpn.backend.linux.networkmanager.protocol.wireguard.local_agent\
    .fallback_local_agent as fallback_local_agent  # pylint: disable=R0402

from proton.vpn.backend.linux.networkmanager.protocol.wireguard.local_agent \
    import AgentConnection, Status, State, AgentConnector, AgentFeatures, \
    ExpiredCertificateError, ReasonCode, APIError  # pylint: disable=R0402

from proton.vpn import logging

logger = logging.getLogger(__name__)


class AgentListener:
    """Listens for local agent messages."""

    def __init__(
            self,
            on_status_change: Awaitable,
            on_error: Awaitable,
            connector: Optional[AgentConnector] = None
    ):
        self._on_status_change = on_status_change
        self._on_error = on_error
        self._connector = connector or AgentConnector()
        self._connection = None
        self._background_task = None

    @property
    def is_running(self):
        """Returns whether the listener is running."""
        return bool(self._background_task)

    @property
    def background_task(self):
        """Returns the background task that listens for local agent messages."""
        return self._background_task

    def start(self, domain: str, credentials: str, features: AgentFeatures):
        """Start listening for local agent messages in the background."""
        if self._background_task:
            logger.warning("Agent listener was already started")
            return

        logger.info("Starting agent listener...")
        self._background_task = asyncio.create_task(
            self._run_in_background(domain, credentials, features)
        )
        self._background_task.add_done_callback(self._on_background_task_stopped)

    async def _run_in_background(self, domain, credentials, features: AgentFeatures):
        """Run the listener in the background."""
        try:
            logger.info("Establishing agent connection...")
            self._connection = await self._connector.connect(domain, credentials)
            logger.info("Agent connection established.")

            if not self._connection:
                # The fallback local agent implementation does not return a connection object.
                # This branch should be removed after removing the fallback implementation.
                await self._notify_status_change(fallback_local_agent.Status(state=State.CONNECTED))
                return

            if features:
                logger.info("Requesting agent features...")
                await self._connection.request_features(features)
                logger.info("Listening on agent connection...")

            await self.listen(self._connection)

        except asyncio.CancelledError:
            logger.info("Agent listener was successfully stopped.")
        except ExpiredCertificateError:
            logger.warning("Expired certificate upon establishing agent connection.")
            message = fallback_local_agent.Status(
                state=State.DISCONNECTED,
                reason=fallback_local_agent.Reason(code=ReasonCode.CERTIFICATE_EXPIRED)
            )
            await self._notify_status_change(message)
        except TimeoutError:
            logger.warning("Agent connection timed out.")
            message = fallback_local_agent.Status(state=State.DISCONNECTED)
            await self._notify_status_change(message)
        except Exception:
            logger.error("Agent listener was unexpectedly closed.")
            message = fallback_local_agent.Status(state=State.DISCONNECTED)
            await self._notify_status_change(message)
            raise
        finally:
            if self._connection:
                self._connection.close()
                self._connection = None

    async def listen(self, connection: AgentConnection):
        """Listens for local agent messages."""
        while True:
            try:
                message = await connection.read()
            except APIError as error:
                await self._notify_error(error)
                continue
            await self._notify_status_change(message)

    async def request_features(self, features: AgentFeatures):
        """Requests the features to be set on the current VPN connection."""
        if features:
            await self._connection.request_features(features)

    def _on_background_task_stopped(self, background_task: asyncio.Task):
        self._background_task = None
        try:
            # Bubble up any unexpected exceptions.
            background_task.result()
        except asyncio.CancelledError:
            logger.info("Agent listener was successfully stopped.")

    def stop(self):
        """Stop listening to the local agent connection."""
        if self._background_task:
            self._background_task.cancel()
            self._background_task = None

    async def _notify_status_change(self, message: Status):
        """Notify all subscribers of a new message."""
        await self._on_status_change(message)

    async def _notify_error(self, error: APIError):
        """Notify all subscribers of a new message."""
        await self._on_error(error)
