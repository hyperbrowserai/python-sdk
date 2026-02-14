import asyncio
from types import SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.computer_action import (
    ComputerActionManager as AsyncComputerActionManager,
)
from hyperbrowser.client.managers.sync_manager.computer_action import (
    ComputerActionManager as SyncComputerActionManager,
)
from hyperbrowser.exceptions import HyperbrowserError


class _DummyClient:
    def __init__(self) -> None:
        self.sessions = None
        self.transport = None


def test_sync_computer_action_manager_raises_hyperbrowser_error_without_endpoint():
    manager = SyncComputerActionManager(_DummyClient())
    session = SimpleNamespace(computer_action_endpoint=None)

    with pytest.raises(
        HyperbrowserError, match="Computer action endpoint not available"
    ):
        manager.screenshot(session)


def test_async_computer_action_manager_raises_hyperbrowser_error_without_endpoint():
    async def run() -> None:
        manager = AsyncComputerActionManager(_DummyClient())
        session = SimpleNamespace(computer_action_endpoint=None)

        with pytest.raises(
            HyperbrowserError, match="Computer action endpoint not available"
        ):
            await manager.screenshot(session)

    asyncio.run(run())


def test_sync_computer_action_manager_rejects_string_subclass_session_ids():
    class _SessionId(str):
        pass

    manager = SyncComputerActionManager(_DummyClient())

    with pytest.raises(
        HyperbrowserError,
        match="session must be a plain string session ID or SessionDetail",
    ):
        manager.screenshot(_SessionId("sess_123"))


def test_async_computer_action_manager_rejects_string_subclass_session_ids():
    class _SessionId(str):
        pass

    async def run() -> None:
        manager = AsyncComputerActionManager(_DummyClient())
        with pytest.raises(
            HyperbrowserError,
            match="session must be a plain string session ID or SessionDetail",
        ):
            await manager.screenshot(_SessionId("sess_123"))

    asyncio.run(run())
