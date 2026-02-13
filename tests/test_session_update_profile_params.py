import asyncio
from types import SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
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


def test_sync_update_profile_params_rejects_conflicting_arguments():
    manager = SyncSessionManager(_SyncClient())

    with pytest.raises(TypeError, match="not both"):
        manager.update_profile_params(
            "session-1",
            UpdateSessionProfileParams(persist_changes=True),
            persist_changes=True,
        )


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
