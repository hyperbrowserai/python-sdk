import asyncio
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable, Tuple, Type

import pytest

from hyperbrowser.client.managers.async_manager.profile import (
    ProfileManager as AsyncProfileManager,
)
from hyperbrowser.client.managers.sync_manager.profile import (
    ProfileManager as SyncProfileManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.profile import CreateProfileParams, ProfileListParams


class _SyncTransport:
    def __init__(self) -> None:
        self.post_calls = []
        self.get_calls = []

    def post(self, url: str, data=None) -> SimpleNamespace:
        self.post_calls.append((url, data))
        return SimpleNamespace(data={"id": "profile_sync_1", "name": "SDK Profile"})

    def get(self, url: str, params=None) -> SimpleNamespace:
        self.get_calls.append((url, params))
        return SimpleNamespace(
            data={
                "profiles": [],
                "totalCount": 0,
                "page": 2,
                "perPage": 5,
            }
        )


class _AsyncTransport:
    def __init__(self) -> None:
        self.post_calls = []
        self.get_calls = []

    async def post(self, url: str, data=None) -> SimpleNamespace:
        self.post_calls.append((url, data))
        return SimpleNamespace(data={"id": "profile_async_1", "name": "SDK Profile"})

    async def get(self, url: str, params=None) -> SimpleNamespace:
        self.get_calls.append((url, params))
        return SimpleNamespace(
            data={
                "profiles": [],
                "totalCount": 0,
                "page": 2,
                "perPage": 5,
            }
        )


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


_SyncCase = Tuple[
    str,
    str,
    Type[Any],
    Callable[[], Any],
    str,
    dict[str, Any],
    str,
]
_AsyncCase = _SyncCase

SYNC_CASES: tuple[_SyncCase, ...] = (
    (
        "create",
        "create",
        CreateProfileParams,
        lambda: CreateProfileParams(name="SDK Profile"),
        "/profile",
        {"name": "SDK Profile"},
        "Failed to serialize profile create params",
    ),
    (
        "list",
        "list",
        ProfileListParams,
        lambda: ProfileListParams(page=2, limit=5, name="sdk"),
        "/profiles",
        {"page": 2, "limit": 5, "name": "sdk"},
        "Failed to serialize profile list params",
    ),
)

ASYNC_CASES: tuple[_AsyncCase, ...] = (
    (
        "create",
        "create",
        CreateProfileParams,
        lambda: CreateProfileParams(name="SDK Profile"),
        "/profile",
        {"name": "SDK Profile"},
        "Failed to serialize profile create params",
    ),
    (
        "list",
        "list",
        ProfileListParams,
        lambda: ProfileListParams(page=2, limit=5, name="sdk"),
        "/profiles",
        {"page": 2, "limit": 5, "name": "sdk"},
        "Failed to serialize profile list params",
    ),
)


@pytest.mark.parametrize(
    "_, method_name, __, build_params, expected_url, expected_payload, ___",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_profile_methods_serialize_params(
    _: str,
    method_name: str,
    __: Type[Any],
    build_params: Callable[[], Any],
    expected_url: str,
    expected_payload: dict[str, Any],
    ___: str,
):
    client = _SyncClient()
    manager = SyncProfileManager(client)

    response = getattr(manager, method_name)(build_params())

    if method_name == "create":
        assert response.id == "profile_sync_1"
        url, payload = client.transport.post_calls[0]
    else:
        assert response.page == 2
        url, payload = client.transport.get_calls[0]

    assert url == expected_url
    assert payload == expected_payload


@pytest.mark.parametrize(
    "_, method_name, params_class, build_params, __, ___, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_profile_methods_wrap_param_serialization_errors(
    _: str,
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncProfileManager(_SyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        getattr(manager, method_name)(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize(
    "_, method_name, params_class, build_params, __, ___, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_profile_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncProfileManager(_SyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        getattr(manager, method_name)(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, method_name, params_class, build_params, __, ___, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_profile_methods_reject_non_dict_serialized_params(
    _: str,
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncProfileManager(_SyncClient())
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"name": "SDK Profile"}),
    )

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        getattr(manager, method_name)(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, method_name, __, build_params, expected_url, expected_payload, ___",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_profile_methods_serialize_params(
    _: str,
    method_name: str,
    __: Type[Any],
    build_params: Callable[[], Any],
    expected_url: str,
    expected_payload: dict[str, Any],
    ___: str,
):
    client = _AsyncClient()
    manager = AsyncProfileManager(client)

    async def run() -> None:
        response = await getattr(manager, method_name)(build_params())
        if method_name == "create":
            assert response.id == "profile_async_1"
            url, payload = client.transport.post_calls[0]
        else:
            assert response.page == 2
            url, payload = client.transport.get_calls[0]

        assert url == expected_url
        assert payload == expected_payload

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, method_name, params_class, build_params, __, ___, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_profile_methods_wrap_param_serialization_errors(
    _: str,
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncProfileManager(_AsyncClient())
    params = build_params()

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await getattr(manager, method_name)(params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, method_name, params_class, build_params, __, ___, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_profile_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncProfileManager(_AsyncClient())
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
            await getattr(manager, method_name)(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, method_name, params_class, build_params, __, ___, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_profile_methods_reject_non_dict_serialized_params(
    _: str,
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncProfileManager(_AsyncClient())
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"name": "SDK Profile"}),
    )

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await getattr(manager, method_name)(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())
