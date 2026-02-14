import asyncio
from types import MappingProxyType, SimpleNamespace
from typing import Any, Awaitable, Callable, Tuple, Type

import pytest

import hyperbrowser.client.managers.session_request_utils as session_request_utils_module
from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import (
    CreateSessionParams,
    SessionEventLogListParams,
    SessionGetParams,
    SessionListParams,
)


class _SyncTransport:
    def __init__(self) -> None:
        self.post_calls = []
        self.get_calls = []

    def post(self, url: str, data=None, files=None) -> SimpleNamespace:
        self.post_calls.append((url, data, files))
        return SimpleNamespace(data={"ok": True})

    def get(self, url: str, params=None, *args) -> SimpleNamespace:
        self.get_calls.append((url, params, args))
        return SimpleNamespace(data={"ok": True})


class _AsyncTransport:
    def __init__(self) -> None:
        self.post_calls = []
        self.get_calls = []

    async def post(self, url: str, data=None, files=None) -> SimpleNamespace:
        self.post_calls.append((url, data, files))
        return SimpleNamespace(data={"ok": True})

    async def get(self, url: str, params=None, *args) -> SimpleNamespace:
        self.get_calls.append((url, params, args))
        return SimpleNamespace(data={"ok": True})


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


def _sync_create(manager: SyncSessionManager, params: Any) -> Any:
    return manager.create(params)


def _sync_get(manager: SyncSessionManager, params: Any) -> Any:
    return manager.get("session_123", params)


def _sync_list(manager: SyncSessionManager, params: Any) -> Any:
    return manager.list(params)


def _sync_event_logs(manager: SyncSessionManager, params: Any) -> Any:
    return manager.event_logs.list("session_123", params)


async def _async_create(manager: AsyncSessionManager, params: Any) -> Any:
    return await manager.create(params)


async def _async_get(manager: AsyncSessionManager, params: Any) -> Any:
    return await manager.get("session_123", params)


async def _async_list(manager: AsyncSessionManager, params: Any) -> Any:
    return await manager.list(params)


async def _async_event_logs(manager: AsyncSessionManager, params: Any) -> Any:
    return await manager.event_logs.list("session_123", params)


_SyncCase = Tuple[
    str,
    Type[Any],
    Callable[[], Any],
    Callable[[SyncSessionManager, Any], Any],
    str,
    str,
    dict[str, Any],
    str,
]
_AsyncCase = Tuple[
    str,
    Type[Any],
    Callable[[], Any],
    Callable[[AsyncSessionManager, Any], Awaitable[Any]],
    str,
    str,
    dict[str, Any],
    str,
]

SYNC_CASES: tuple[_SyncCase, ...] = (
    (
        "create",
        CreateSessionParams,
        lambda: CreateSessionParams(),
        _sync_create,
        "post",
        "/session",
        {"useStealth": True},
        "Failed to serialize session create params",
    ),
    (
        "get",
        SessionGetParams,
        lambda: SessionGetParams(live_view_ttl_seconds=60),
        _sync_get,
        "get",
        "/session/session_123",
        {"liveViewTtlSeconds": 60},
        "Failed to serialize session get params",
    ),
    (
        "list",
        SessionListParams,
        lambda: SessionListParams(page=2, limit=5),
        _sync_list,
        "get",
        "/sessions",
        {"page": 2, "limit": 5},
        "Failed to serialize session list params",
    ),
    (
        "event-logs",
        SessionEventLogListParams,
        lambda: SessionEventLogListParams(page=2),
        _sync_event_logs,
        "get",
        "/session/session_123/event-logs",
        {"page": 2},
        "Failed to serialize session event log params",
    ),
)

ASYNC_CASES: tuple[_AsyncCase, ...] = (
    (
        "create",
        CreateSessionParams,
        lambda: CreateSessionParams(),
        _async_create,
        "post",
        "/session",
        {"useStealth": True},
        "Failed to serialize session create params",
    ),
    (
        "get",
        SessionGetParams,
        lambda: SessionGetParams(live_view_ttl_seconds=60),
        _async_get,
        "get",
        "/session/session_123",
        {"liveViewTtlSeconds": 60},
        "Failed to serialize session get params",
    ),
    (
        "list",
        SessionListParams,
        lambda: SessionListParams(page=2, limit=5),
        _async_list,
        "get",
        "/sessions",
        {"page": 2, "limit": 5},
        "Failed to serialize session list params",
    ),
    (
        "event-logs",
        SessionEventLogListParams,
        lambda: SessionEventLogListParams(page=2),
        _async_event_logs,
        "get",
        "/session/session_123/event-logs",
        {"page": 2},
        "Failed to serialize session event log params",
    ),
)


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, transport_method, expected_url, expected_payload, ___",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_session_methods_serialize_params(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[SyncSessionManager, Any], Any],
    transport_method: str,
    expected_url: str,
    expected_payload: dict[str, Any],
    ___: str,
    monkeypatch: pytest.MonkeyPatch,
):
    client = _SyncClient()
    manager = SyncSessionManager(client)
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: dict(expected_payload),
    )
    monkeypatch.setattr(
        session_request_utils_module,
        "parse_session_response_model",
        lambda data, model, operation_name: {"data": data, "operation": operation_name},
    )

    response = call_method(manager, params)

    assert response["data"] == {"ok": True}
    if transport_method == "post":
        url, payload, _ = client.transport.post_calls[0]
    else:
        url, payload, _ = client.transport.get_calls[0]
    assert url == expected_url
    assert payload == expected_payload


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, __, ___, ____, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_session_methods_wrap_serialization_errors(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[SyncSessionManager, Any], Any],
    __: str,
    ___: str,
    ____: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncSessionManager(_SyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        call_method(manager, params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, __, ___, ____, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_session_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[SyncSessionManager, Any], Any],
    __: str,
    ___: str,
    ____: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncSessionManager(_SyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        call_method(manager, params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, __, ___, ____, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_session_methods_reject_non_dict_serialized_params(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[SyncSessionManager, Any], Any],
    __: str,
    ___: str,
    ____: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncSessionManager(_SyncClient())
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"value": "not-dict"}),
    )

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        call_method(manager, params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, transport_method, expected_url, expected_payload, ___",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_session_methods_serialize_params(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[AsyncSessionManager, Any], Awaitable[Any]],
    transport_method: str,
    expected_url: str,
    expected_payload: dict[str, Any],
    ___: str,
    monkeypatch: pytest.MonkeyPatch,
):
    client = _AsyncClient()
    manager = AsyncSessionManager(client)
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: dict(expected_payload),
    )
    monkeypatch.setattr(
        session_request_utils_module,
        "parse_session_response_model",
        lambda data, model, operation_name: {"data": data, "operation": operation_name},
    )

    async def run() -> None:
        response = await call_method(manager, params)
        assert response["data"] == {"ok": True}
        if transport_method == "post":
            url, payload, _ = client.transport.post_calls[0]
        else:
            url, payload, _ = client.transport.get_calls[0]
        assert url == expected_url
        assert payload == expected_payload

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, __, ___, ____, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_session_methods_wrap_serialization_errors(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[AsyncSessionManager, Any], Awaitable[Any]],
    __: str,
    ___: str,
    ____: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncSessionManager(_AsyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await call_method(manager, params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, __, ___, ____, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_session_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[AsyncSessionManager, Any], Awaitable[Any]],
    __: str,
    ___: str,
    ____: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncSessionManager(_AsyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await call_method(manager, params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, params_class, build_params, call_method, __, ___, ____, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_session_methods_reject_non_dict_serialized_params(
    _: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    call_method: Callable[[AsyncSessionManager, Any], Awaitable[Any]],
    __: str,
    ___: str,
    ____: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncSessionManager(_AsyncClient())
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"value": "not-dict"}),
    )

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await call_method(manager, params)
        assert exc_info.value.original_error is None

    asyncio.run(run())
