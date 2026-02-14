import asyncio
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable, Tuple, Type

import pytest

from hyperbrowser.client.managers.async_manager.web import WebManager as AsyncWebManager
from hyperbrowser.client.managers.async_manager.web.batch_fetch import (
    BatchFetchManager as AsyncBatchFetchManager,
)
from hyperbrowser.client.managers.async_manager.web.crawl import (
    WebCrawlManager as AsyncWebCrawlManager,
)
from hyperbrowser.client.managers.sync_manager.web import WebManager as SyncWebManager
from hyperbrowser.client.managers.sync_manager.web.batch_fetch import (
    BatchFetchManager as SyncBatchFetchManager,
)
from hyperbrowser.client.managers.sync_manager.web.crawl import (
    WebCrawlManager as SyncWebCrawlManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    FetchParams,
    GetBatchFetchJobParams,
    GetWebCrawlJobParams,
    StartBatchFetchJobParams,
    StartWebCrawlJobParams,
    WebSearchParams,
)


class _SyncTransport:
    def __init__(self) -> None:
        self.post_calls = []
        self.get_calls = []

    def post(self, url: str, data=None) -> SimpleNamespace:
        self.post_calls.append((url, data))
        if url == "/web/fetch":
            return SimpleNamespace(
                data={"jobId": "job_sync_fetch", "status": "completed"}
            )
        if url == "/web/search":
            return SimpleNamespace(
                data={
                    "jobId": "job_sync_search",
                    "status": "completed",
                    "data": {"query": "docs", "results": []},
                }
            )
        return SimpleNamespace(data={"jobId": "job_sync_start"})

    def get(self, url: str, params=None) -> SimpleNamespace:
        self.get_calls.append((url, params))
        return SimpleNamespace(
            data={
                "jobId": "job_sync_get",
                "status": "completed",
                "data": [],
                "currentPageBatch": 1,
                "totalPageBatches": 1,
                "totalPages": 0,
                "batchSize": 100,
            }
        )


class _AsyncTransport:
    def __init__(self) -> None:
        self.post_calls = []
        self.get_calls = []

    async def post(self, url: str, data=None) -> SimpleNamespace:
        self.post_calls.append((url, data))
        if url == "/web/fetch":
            return SimpleNamespace(
                data={"jobId": "job_async_fetch", "status": "completed"}
            )
        if url == "/web/search":
            return SimpleNamespace(
                data={
                    "jobId": "job_async_search",
                    "status": "completed",
                    "data": {"query": "docs", "results": []},
                }
            )
        return SimpleNamespace(data={"jobId": "job_async_start"})

    async def get(self, url: str, params=None) -> SimpleNamespace:
        self.get_calls.append((url, params))
        return SimpleNamespace(
            data={
                "jobId": "job_async_get",
                "status": "completed",
                "data": [],
                "currentPageBatch": 1,
                "totalPageBatches": 1,
                "totalPages": 0,
                "batchSize": 100,
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


_SyncPostCase = Tuple[
    str,
    Type[Any],
    str,
    Type[Any],
    Callable[[], Any],
    str,
    dict[str, Any],
    str,
    str,
]
_AsyncPostCase = _SyncPostCase

SYNC_POST_CASES: tuple[_SyncPostCase, ...] = (
    (
        "web-fetch",
        SyncWebManager,
        "fetch",
        FetchParams,
        lambda: FetchParams(url="https://example.com"),
        "/web/fetch",
        {"url": "https://example.com"},
        "job_sync_fetch",
        "Failed to serialize web fetch params",
    ),
    (
        "web-search",
        SyncWebManager,
        "search",
        WebSearchParams,
        lambda: WebSearchParams(query="sdk docs"),
        "/web/search",
        {"query": "sdk docs"},
        "job_sync_search",
        "Failed to serialize web search params",
    ),
    (
        "batch-fetch-start",
        SyncBatchFetchManager,
        "start",
        StartBatchFetchJobParams,
        lambda: StartBatchFetchJobParams(urls=["https://example.com"]),
        "/web/batch-fetch",
        {"urls": ["https://example.com"]},
        "job_sync_start",
        "Failed to serialize batch fetch start params",
    ),
    (
        "web-crawl-start",
        SyncWebCrawlManager,
        "start",
        StartWebCrawlJobParams,
        lambda: StartWebCrawlJobParams(url="https://example.com"),
        "/web/crawl",
        {"url": "https://example.com"},
        "job_sync_start",
        "Failed to serialize web crawl start params",
    ),
)

ASYNC_POST_CASES: tuple[_AsyncPostCase, ...] = (
    (
        "web-fetch",
        AsyncWebManager,
        "fetch",
        FetchParams,
        lambda: FetchParams(url="https://example.com"),
        "/web/fetch",
        {"url": "https://example.com"},
        "job_async_fetch",
        "Failed to serialize web fetch params",
    ),
    (
        "web-search",
        AsyncWebManager,
        "search",
        WebSearchParams,
        lambda: WebSearchParams(query="sdk docs"),
        "/web/search",
        {"query": "sdk docs"},
        "job_async_search",
        "Failed to serialize web search params",
    ),
    (
        "batch-fetch-start",
        AsyncBatchFetchManager,
        "start",
        StartBatchFetchJobParams,
        lambda: StartBatchFetchJobParams(urls=["https://example.com"]),
        "/web/batch-fetch",
        {"urls": ["https://example.com"]},
        "job_async_start",
        "Failed to serialize batch fetch start params",
    ),
    (
        "web-crawl-start",
        AsyncWebCrawlManager,
        "start",
        StartWebCrawlJobParams,
        lambda: StartWebCrawlJobParams(url="https://example.com"),
        "/web/crawl",
        {"url": "https://example.com"},
        "job_async_start",
        "Failed to serialize web crawl start params",
    ),
)


@pytest.mark.parametrize(
    "_, manager_class, method_name, __, build_params, expected_url, expected_payload, expected_job_id, ___",
    SYNC_POST_CASES,
    ids=[case[0] for case in SYNC_POST_CASES],
)
def test_sync_web_post_methods_serialize_params(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    __: Type[Any],
    build_params: Callable[[], Any],
    expected_url: str,
    expected_payload: dict[str, Any],
    expected_job_id: str,
    ___: str,
):
    client = _SyncClient()
    manager = manager_class(client)

    response = getattr(manager, method_name)(build_params())

    assert response.job_id == expected_job_id
    url, payload = client.transport.post_calls[0]
    assert url == expected_url
    assert payload == expected_payload


@pytest.mark.parametrize(
    "_, manager_class, method_name, params_class, build_params, __, ___, ____, expected_error",
    SYNC_POST_CASES,
    ids=[case[0] for case in SYNC_POST_CASES],
)
def test_sync_web_post_methods_wrap_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    ____: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())
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
    "_, manager_class, method_name, params_class, build_params, __, ___, ____, expected_error",
    SYNC_POST_CASES,
    ids=[case[0] for case in SYNC_POST_CASES],
)
def test_sync_web_post_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    ____: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())
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
    "_, manager_class, method_name, params_class, build_params, __, ___, ____, expected_error",
    SYNC_POST_CASES,
    ids=[case[0] for case in SYNC_POST_CASES],
)
def test_sync_web_post_methods_reject_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    ____: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"url": "https://example.com"}),
    )

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        getattr(manager, method_name)(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, method_name, __, build_params, expected_url, expected_payload, expected_job_id, ___",
    ASYNC_POST_CASES,
    ids=[case[0] for case in ASYNC_POST_CASES],
)
def test_async_web_post_methods_serialize_params(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    __: Type[Any],
    build_params: Callable[[], Any],
    expected_url: str,
    expected_payload: dict[str, Any],
    expected_job_id: str,
    ___: str,
):
    client = _AsyncClient()
    manager = manager_class(client)

    async def run() -> None:
        response = await getattr(manager, method_name)(build_params())
        assert response.job_id == expected_job_id
        url, payload = client.transport.post_calls[0]
        assert url == expected_url
        assert payload == expected_payload

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, method_name, params_class, build_params, __, ___, ____, expected_error",
    ASYNC_POST_CASES,
    ids=[case[0] for case in ASYNC_POST_CASES],
)
def test_async_web_post_methods_wrap_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    ____: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())
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
    "_, manager_class, method_name, params_class, build_params, __, ___, ____, expected_error",
    ASYNC_POST_CASES,
    ids=[case[0] for case in ASYNC_POST_CASES],
)
def test_async_web_post_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    ____: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())
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
    "_, manager_class, method_name, params_class, build_params, __, ___, ____, expected_error",
    ASYNC_POST_CASES,
    ids=[case[0] for case in ASYNC_POST_CASES],
)
def test_async_web_post_methods_reject_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    method_name: str,
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
    ____: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())
    params = build_params()

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"url": "https://example.com"}),
    )

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await getattr(manager, method_name)(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


_SyncGetCase = Tuple[
    str,
    Type[Any],
    Type[Any],
    Callable[[], Any],
    str,
]
_AsyncGetCase = _SyncGetCase

SYNC_GET_CASES: tuple[_SyncGetCase, ...] = (
    (
        "batch-fetch-get",
        SyncBatchFetchManager,
        GetBatchFetchJobParams,
        lambda: GetBatchFetchJobParams(page=1),
        "Failed to serialize batch fetch get params",
    ),
    (
        "web-crawl-get",
        SyncWebCrawlManager,
        GetWebCrawlJobParams,
        lambda: GetWebCrawlJobParams(page=1),
        "Failed to serialize web crawl get params",
    ),
)

ASYNC_GET_CASES: tuple[_AsyncGetCase, ...] = (
    (
        "batch-fetch-get",
        AsyncBatchFetchManager,
        GetBatchFetchJobParams,
        lambda: GetBatchFetchJobParams(page=1),
        "Failed to serialize batch fetch get params",
    ),
    (
        "web-crawl-get",
        AsyncWebCrawlManager,
        GetWebCrawlJobParams,
        lambda: GetWebCrawlJobParams(page=1),
        "Failed to serialize web crawl get params",
    ),
)


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    SYNC_GET_CASES,
    ids=[case[0] for case in SYNC_GET_CASES],
)
def test_sync_web_get_methods_wrap_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        manager.get("job_123", build_params())

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    SYNC_GET_CASES,
    ids=[case[0] for case in SYNC_GET_CASES],
)
def test_sync_web_get_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        manager.get("job_123", build_params())

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    SYNC_GET_CASES,
    ids=[case[0] for case in SYNC_GET_CASES],
)
def test_sync_web_get_methods_reject_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"page": 1}),
    )

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        manager.get("job_123", build_params())

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    ASYNC_GET_CASES,
    ids=[case[0] for case in ASYNC_GET_CASES],
)
def test_async_web_get_methods_wrap_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await manager.get("job_123", build_params())
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    ASYNC_GET_CASES,
    ids=[case[0] for case in ASYNC_GET_CASES],
)
def test_async_web_get_methods_preserve_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await manager.get("job_123", build_params())
        assert exc_info.value.original_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    ASYNC_GET_CASES,
    ids=[case[0] for case in ASYNC_GET_CASES],
)
def test_async_web_get_methods_reject_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"page": 1}),
    )

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await manager.get("job_123", build_params())
        assert exc_info.value.original_error is None

    asyncio.run(run())
