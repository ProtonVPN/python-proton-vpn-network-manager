from asyncio import CancelledError
from unittest.mock import AsyncMock, Mock

import pytest

from proton.vpn.backend.linux.networkmanager.protocol.wireguard.local_agent.fallback_local_agent import Status, State
from proton.vpn.backend.linux.networkmanager.protocol.wireguard.local_agent.listener import AgentListener


@pytest.mark.asyncio
async def test_listen_notifies_status_message_to_subscribers():
    # Given
    subscriber = AsyncMock()
    listener = AgentListener(subscribers=[subscriber], connector=AsyncMock())
    message = Status(State.CONNECTED)
    read_called: bool = False

    async def read_mock():
        nonlocal read_called
        if not read_called:
            read_called = True
            return message
        else:
            raise CancelledError("Connection closed")

    agent_connection = AsyncMock()
    agent_connection.read.side_effect = read_mock

    # When
    try:
        await listener.listen(agent_connection)
    except CancelledError:
        pass

    # Then
    subscriber.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_stop_cancels_background_task():
    # Given
    listener = AgentListener(connector=AsyncMock())

    listener.start("domain", "credentials", features=Mock())
    assert listener.background_task

    # When
    background_task = listener.background_task
    listener.stop()

    # Then
    assert background_task.cancelled
