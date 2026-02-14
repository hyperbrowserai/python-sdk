import asyncio
from types import MappingProxyType, SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.agents.cua import (
    CuaManager as AsyncCuaManager,
)
from hyperbrowser.client.managers.sync_manager.agents.cua import (
    CuaManager as SyncCuaManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.agents.cua import StartCuaTaskParams


class _SyncTransport:
    def __init__(self) -> None:
        self.calls = []

    def post(self, url: str, data=None) -> SimpleNamespace:
        self.calls.append((url, data))
        return SimpleNamespace(data={"jobId": "job_sync_1"})


class _AsyncTransport:
    def __init__(self) -> None:
        self.calls = []

    async def post(self, url: str, data=None) -> SimpleNamespace:
        self.calls.append((url, data))
        return SimpleNamespace(data={"jobId": "job_async_1"})


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


def test_sync_cua_start_serializes_params():
    client = _SyncClient()
    manager = SyncCuaManager(client)

    response = manager.start(StartCuaTaskParams(task="open docs"))

    assert response.job_id == "job_sync_1"
    _, payload = client.transport.calls[0]
    assert payload == {"task": "open docs"}


def test_async_cua_start_serializes_params():
    client = _AsyncClient()
    manager = AsyncCuaManager(client)

    async def run() -> None:
        response = await manager.start(StartCuaTaskParams(task="open docs"))
        assert response.job_id == "job_async_1"
        _, payload = client.transport.calls[0]
        assert payload == {"task": "open docs"}

    asyncio.run(run())


def test_sync_cua_start_wraps_param_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncCuaManager(_SyncClient())
    params = StartCuaTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(StartCuaTaskParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize CUA start params"
    ) as exc_info:
        manager.start(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_sync_cua_start_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncCuaManager(_SyncClient())
    params = StartCuaTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(StartCuaTaskParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        manager.start(params)

    assert exc_info.value.original_error is None


def test_sync_cua_start_rejects_non_dict_serialized_params(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncCuaManager(_SyncClient())
    params = StartCuaTaskParams(task="open docs")

    monkeypatch.setattr(
        StartCuaTaskParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"task": "open docs"}),
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize CUA start params"
    ) as exc_info:
        manager.start(params)

    assert exc_info.value.original_error is None


def test_async_cua_start_wraps_param_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncCuaManager(_AsyncClient())
    params = StartCuaTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(StartCuaTaskParams, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="Failed to serialize CUA start params"
        ) as exc_info:
            await manager.start(params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


def test_async_cua_start_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncCuaManager(_AsyncClient())
    params = StartCuaTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(StartCuaTaskParams, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await manager.start(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


def test_async_cua_start_rejects_non_dict_serialized_params(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncCuaManager(_AsyncClient())
    params = StartCuaTaskParams(task="open docs")

    monkeypatch.setattr(
        StartCuaTaskParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"task": "open docs"}),
    )

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="Failed to serialize CUA start params"
        ) as exc_info:
            await manager.start(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())
