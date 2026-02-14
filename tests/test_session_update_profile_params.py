import asyncio
from types import SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import UpdateSessionProfileParams


class _SyncTransport:
    def __init__(self) -> None:
        self.calls = []

    def put(self, url: str, data=None) -> SimpleNamespace:
        self.calls.append((url, data))
        return SimpleNamespace(data={"success": True})


class _AsyncTransport:
    def __init__(self) -> None:
        self.calls = []

    async def put(self, url: str, data=None) -> SimpleNamespace:
        self.calls.append((url, data))
        return SimpleNamespace(data={"success": True})


class _SyncClient:
    def __init__(self) -> None:
        self.transport = _SyncTransport()

    def _build_url(self, path: str) -> str:
        return path


class _AsyncClient:
    def __init__(self) -> None:
        self.transport = _AsyncTransport()

    def _build_url(self, path: str) -> str:
        return path


def test_sync_update_profile_params_uses_serialized_param_model():
    client = _SyncClient()
    manager = SyncSessionManager(client)

    manager.update_profile_params(
        "session-1",
        UpdateSessionProfileParams(persist_changes=True),
    )

    _, payload = client.transport.calls[0]
    assert payload == {"type": "profile", "params": {"persistChanges": True}}


def test_sync_update_profile_params_bool_warns_and_serializes():
    SyncSessionManager._has_warned_update_profile_params_boolean_deprecated = False
    client = _SyncClient()
    manager = SyncSessionManager(client)

    with pytest.warns(DeprecationWarning):
        manager.update_profile_params("session-1", True)

    _, payload = client.transport.calls[0]
    assert payload == {"type": "profile", "params": {"persistChanges": True}}


def test_sync_update_profile_params_bool_deprecation_warning_only_emitted_once():
    SyncSessionManager._has_warned_update_profile_params_boolean_deprecated = False
    client = _SyncClient()
    manager = SyncSessionManager(client)

    with pytest.warns(DeprecationWarning) as warning_records:
        manager.update_profile_params("session-1", True)
        manager.update_profile_params("session-2", True)

    assert len(warning_records) == 1


def test_sync_update_profile_params_rejects_conflicting_arguments():
    manager = SyncSessionManager(_SyncClient())

    with pytest.raises(HyperbrowserError, match="not both"):
        manager.update_profile_params(
            "session-1",
            UpdateSessionProfileParams(persist_changes=True),
            persist_changes=True,
        )


def test_sync_update_profile_params_rejects_subclass_params():
    class _Params(UpdateSessionProfileParams):
        pass

    manager = SyncSessionManager(_SyncClient())

    with pytest.raises(HyperbrowserError, match="plain UpdateSessionProfileParams"):
        manager.update_profile_params("session-1", _Params(persist_changes=True))


def test_sync_update_profile_params_wraps_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncSessionManager(_SyncClient())
    params = UpdateSessionProfileParams(persist_changes=True)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(
        UpdateSessionProfileParams, "model_dump", _raise_model_dump_error
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize update_profile_params payload"
    ) as exc_info:
        manager.update_profile_params("session-1", params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_sync_update_profile_params_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncSessionManager(_SyncClient())
    params = UpdateSessionProfileParams(persist_changes=True)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(
        UpdateSessionProfileParams, "model_dump", _raise_model_dump_error
    )

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        manager.update_profile_params("session-1", params)

    assert exc_info.value.original_error is None


def test_async_update_profile_params_bool_warns_and_serializes():
    AsyncSessionManager._has_warned_update_profile_params_boolean_deprecated = False
    client = _AsyncClient()
    manager = AsyncSessionManager(client)

    async def run() -> None:
        with pytest.warns(DeprecationWarning):
            await manager.update_profile_params("session-1", True)

    asyncio.run(run())

    _, payload = client.transport.calls[0]
    assert payload == {"type": "profile", "params": {"persistChanges": True}}


def test_async_update_profile_params_bool_deprecation_warning_only_emitted_once():
    AsyncSessionManager._has_warned_update_profile_params_boolean_deprecated = False
    client = _AsyncClient()
    manager = AsyncSessionManager(client)

    async def run() -> None:
        with pytest.warns(DeprecationWarning) as warning_records:
            await manager.update_profile_params("session-1", True)
            await manager.update_profile_params("session-2", True)
        assert len(warning_records) == 1

    asyncio.run(run())


def test_async_update_profile_params_rejects_conflicting_arguments():
    manager = AsyncSessionManager(_AsyncClient())

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match="not both"):
            await manager.update_profile_params(
                "session-1",
                UpdateSessionProfileParams(persist_changes=True),
                persist_changes=True,
            )

    asyncio.run(run())


def test_async_update_profile_params_rejects_subclass_params():
    class _Params(UpdateSessionProfileParams):
        pass

    manager = AsyncSessionManager(_AsyncClient())

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match="plain UpdateSessionProfileParams"):
            await manager.update_profile_params(
                "session-1",
                _Params(persist_changes=True),
            )

    asyncio.run(run())


def test_async_update_profile_params_wraps_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncSessionManager(_AsyncClient())
    params = UpdateSessionProfileParams(persist_changes=True)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(
        UpdateSessionProfileParams, "model_dump", _raise_model_dump_error
    )

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="Failed to serialize update_profile_params payload"
        ) as exc_info:
            await manager.update_profile_params("session-1", params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


def test_async_update_profile_params_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncSessionManager(_AsyncClient())
    params = UpdateSessionProfileParams(persist_changes=True)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(
        UpdateSessionProfileParams, "model_dump", _raise_model_dump_error
    )

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await manager.update_profile_params("session-1", params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


def test_sync_update_profile_params_requires_argument_or_keyword():
    manager = SyncSessionManager(_SyncClient())

    with pytest.raises(HyperbrowserError, match="requires either"):
        manager.update_profile_params("session-1")


def test_async_update_profile_params_requires_argument_or_keyword():
    manager = AsyncSessionManager(_AsyncClient())

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match="requires either"):
            await manager.update_profile_params("session-1")

    asyncio.run(run())
