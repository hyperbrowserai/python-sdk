import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

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


def test_sync_computer_action_manager_wraps_missing_endpoint_attribute():
    manager = SyncComputerActionManager(_DummyClient())

    with pytest.raises(
        HyperbrowserError, match="session must include computer_action_endpoint"
    ) as exc_info:
        manager.screenshot(SimpleNamespace())

    assert isinstance(exc_info.value.original_error, AttributeError)


def test_async_computer_action_manager_wraps_missing_endpoint_attribute():
    async def run() -> None:
        manager = AsyncComputerActionManager(_DummyClient())
        with pytest.raises(
            HyperbrowserError, match="session must include computer_action_endpoint"
        ) as exc_info:
            await manager.screenshot(SimpleNamespace())
        assert isinstance(exc_info.value.original_error, AttributeError)

    asyncio.run(run())


def test_sync_computer_action_manager_rejects_non_string_endpoints():
    manager = SyncComputerActionManager(_DummyClient())

    with pytest.raises(
        HyperbrowserError, match="session computer_action_endpoint must be a string"
    ) as exc_info:
        manager.screenshot(SimpleNamespace(computer_action_endpoint=123))

    assert exc_info.value.original_error is None


def test_async_computer_action_manager_rejects_non_string_endpoints():
    async def run() -> None:
        manager = AsyncComputerActionManager(_DummyClient())
        with pytest.raises(
            HyperbrowserError, match="session computer_action_endpoint must be a string"
        ) as exc_info:
            await manager.screenshot(SimpleNamespace(computer_action_endpoint=123))
        assert exc_info.value.original_error is None

    asyncio.run(run())


def test_sync_computer_action_manager_rejects_string_subclass_endpoints():
    class _Endpoint(str):
        pass

    manager = SyncComputerActionManager(_DummyClient())

    with pytest.raises(
        HyperbrowserError, match="session computer_action_endpoint must be a string"
    ) as exc_info:
        manager.screenshot(
            SimpleNamespace(
                computer_action_endpoint=_Endpoint("https://example.com/cua")
            )
        )

    assert exc_info.value.original_error is None


def test_sync_computer_action_manager_rejects_whitespace_wrapped_endpoints():
    manager = SyncComputerActionManager(_DummyClient())

    with pytest.raises(
        HyperbrowserError,
        match="session computer_action_endpoint must not contain leading or trailing whitespace",
    ) as exc_info:
        manager.screenshot(
            SimpleNamespace(computer_action_endpoint="  https://example.com/cua  ")
        )

    assert exc_info.value.original_error is None


def test_async_computer_action_manager_rejects_control_character_endpoints():
    async def run() -> None:
        manager = AsyncComputerActionManager(_DummyClient())
        with pytest.raises(
            HyperbrowserError,
            match="session computer_action_endpoint must not contain control characters",
        ) as exc_info:
            await manager.screenshot(
                SimpleNamespace(computer_action_endpoint="https://exa\tmple.com/cua")
            )
        assert exc_info.value.original_error is None

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


def test_sync_computer_action_manager_wraps_param_serialization_errors():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            raise RuntimeError("broken model_dump")

    manager = SyncComputerActionManager(_DummyClient())
    session = SimpleNamespace(computer_action_endpoint="https://example.com/cua")

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize computer action params"
    ) as exc_info:
        manager._execute_request(session, _BrokenParams())  # type: ignore[arg-type]

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_sync_computer_action_manager_preserves_hyperbrowser_param_serialization_errors():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            raise HyperbrowserError("custom model_dump failure")

    manager = SyncComputerActionManager(_DummyClient())
    session = SimpleNamespace(computer_action_endpoint="https://example.com/cua")

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        manager._execute_request(session, _BrokenParams())  # type: ignore[arg-type]

    assert exc_info.value.original_error is None


def test_async_computer_action_manager_wraps_param_serialization_errors():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            raise RuntimeError("broken model_dump")

    manager = AsyncComputerActionManager(_DummyClient())
    session = SimpleNamespace(computer_action_endpoint="https://example.com/cua")

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="Failed to serialize computer action params"
        ) as exc_info:
            await manager._execute_request(session, _BrokenParams())  # type: ignore[arg-type]
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


def test_async_computer_action_manager_preserves_hyperbrowser_param_serialization_errors():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            raise HyperbrowserError("custom model_dump failure")

    manager = AsyncComputerActionManager(_DummyClient())
    session = SimpleNamespace(computer_action_endpoint="https://example.com/cua")

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await manager._execute_request(session, _BrokenParams())  # type: ignore[arg-type]
        assert exc_info.value.original_error is None

    asyncio.run(run())
