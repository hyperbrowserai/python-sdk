import asyncio
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable, Tuple, Type

import pytest

from hyperbrowser.client.managers.async_manager.crawl import (
    CrawlManager as AsyncCrawlManager,
)
from hyperbrowser.client.managers.async_manager.extract import (
    ExtractManager as AsyncExtractManager,
)
from hyperbrowser.client.managers.async_manager.scrape import (
    BatchScrapeManager as AsyncBatchScrapeManager,
)
from hyperbrowser.client.managers.async_manager.scrape import (
    ScrapeManager as AsyncScrapeManager,
)
from hyperbrowser.client.managers.sync_manager.crawl import (
    CrawlManager as SyncCrawlManager,
)
from hyperbrowser.client.managers.sync_manager.extract import (
    ExtractManager as SyncExtractManager,
)
from hyperbrowser.client.managers.sync_manager.scrape import (
    BatchScrapeManager as SyncBatchScrapeManager,
)
from hyperbrowser.client.managers.sync_manager.scrape import (
    ScrapeManager as SyncScrapeManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.crawl import GetCrawlJobParams, StartCrawlJobParams
from hyperbrowser.models.extract import StartExtractJobParams
from hyperbrowser.models.scrape import (
    GetBatchScrapeJobParams,
    StartBatchScrapeJobParams,
    StartScrapeJobParams,
)


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


_SyncCase = Tuple[
    str,
    Type[Any],
    Type[Any],
    Callable[[], Any],
    str,
    dict[str, Any],
    str,
]
_AsyncCase = _SyncCase

SYNC_CASES: tuple[_SyncCase, ...] = (
    (
        "scrape",
        SyncScrapeManager,
        StartScrapeJobParams,
        lambda: StartScrapeJobParams(url="https://example.com"),
        "/scrape",
        {"url": "https://example.com"},
        "Failed to serialize scrape start params",
    ),
    (
        "batch-scrape",
        SyncBatchScrapeManager,
        StartBatchScrapeJobParams,
        lambda: StartBatchScrapeJobParams(urls=["https://example.com"]),
        "/scrape/batch",
        {"urls": ["https://example.com"]},
        "Failed to serialize batch scrape start params",
    ),
    (
        "crawl",
        SyncCrawlManager,
        StartCrawlJobParams,
        lambda: StartCrawlJobParams(url="https://example.com"),
        "/crawl",
        {
            "url": "https://example.com",
            "followLinks": True,
            "ignoreSitemap": False,
            "excludePatterns": [],
            "includePatterns": [],
        },
        "Failed to serialize crawl start params",
    ),
    (
        "extract",
        SyncExtractManager,
        StartExtractJobParams,
        lambda: StartExtractJobParams(
            urls=["https://example.com"],
            prompt="extract data",
        ),
        "/extract",
        {"urls": ["https://example.com"], "prompt": "extract data"},
        "Failed to serialize extract start params",
    ),
)

ASYNC_CASES: tuple[_AsyncCase, ...] = (
    (
        "scrape",
        AsyncScrapeManager,
        StartScrapeJobParams,
        lambda: StartScrapeJobParams(url="https://example.com"),
        "/scrape",
        {"url": "https://example.com"},
        "Failed to serialize scrape start params",
    ),
    (
        "batch-scrape",
        AsyncBatchScrapeManager,
        StartBatchScrapeJobParams,
        lambda: StartBatchScrapeJobParams(urls=["https://example.com"]),
        "/scrape/batch",
        {"urls": ["https://example.com"]},
        "Failed to serialize batch scrape start params",
    ),
    (
        "crawl",
        AsyncCrawlManager,
        StartCrawlJobParams,
        lambda: StartCrawlJobParams(url="https://example.com"),
        "/crawl",
        {
            "url": "https://example.com",
            "followLinks": True,
            "ignoreSitemap": False,
            "excludePatterns": [],
            "includePatterns": [],
        },
        "Failed to serialize crawl start params",
    ),
    (
        "extract",
        AsyncExtractManager,
        StartExtractJobParams,
        lambda: StartExtractJobParams(
            urls=["https://example.com"],
            prompt="extract data",
        ),
        "/extract",
        {"urls": ["https://example.com"], "prompt": "extract data"},
        "Failed to serialize extract start params",
    ),
)

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
        "batch-scrape-get",
        SyncBatchScrapeManager,
        GetBatchScrapeJobParams,
        lambda: GetBatchScrapeJobParams(page=1),
        "Failed to serialize batch scrape get params",
    ),
    (
        "crawl-get",
        SyncCrawlManager,
        GetCrawlJobParams,
        lambda: GetCrawlJobParams(page=1),
        "Failed to serialize crawl get params",
    ),
)

ASYNC_GET_CASES: tuple[_AsyncGetCase, ...] = (
    (
        "batch-scrape-get",
        AsyncBatchScrapeManager,
        GetBatchScrapeJobParams,
        lambda: GetBatchScrapeJobParams(page=1),
        "Failed to serialize batch scrape get params",
    ),
    (
        "crawl-get",
        AsyncCrawlManager,
        GetCrawlJobParams,
        lambda: GetCrawlJobParams(page=1),
        "Failed to serialize crawl get params",
    ),
)


@pytest.mark.parametrize(
    "_, manager_class, __, build_params, expected_url, expected_payload, ___",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_job_start_serializes_params(
    _: str,
    manager_class: Type[Any],
    __: Type[Any],
    build_params: Callable[[], Any],
    expected_url: str,
    expected_payload: dict[str, Any],
    ___: str,
):
    client = _SyncClient()
    manager = manager_class(client)

    response = manager.start(build_params())

    assert response.job_id == "job_sync_1"
    url, payload = client.transport.calls[0]
    assert url == expected_url
    assert payload == expected_payload


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, __, ___, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_job_start_wraps_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
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
        manager.start(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, __, ___, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_job_start_preserves_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
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
        manager.start(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, __, ___, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_job_start_rejects_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
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
        manager.start(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, __, build_params, expected_url, expected_payload, ___",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_job_start_serializes_params(
    _: str,
    manager_class: Type[Any],
    __: Type[Any],
    build_params: Callable[[], Any],
    expected_url: str,
    expected_payload: dict[str, Any],
    ___: str,
):
    client = _AsyncClient()
    manager = manager_class(client)

    async def run() -> None:
        response = await manager.start(build_params())
        assert response.job_id == "job_async_1"
        url, payload = client.transport.calls[0]
        assert url == expected_url
        assert payload == expected_payload

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, __, ___, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_job_start_wraps_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
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
            await manager.start(params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, __, ___, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_job_start_preserves_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
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
            await manager.start(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, __, ___, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_job_start_rejects_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    build_params: Callable[[], Any],
    __: str,
    ___: dict[str, Any],
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
            await manager.start(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, build_params, expected_error",
    SYNC_GET_CASES,
    ids=[case[0] for case in SYNC_GET_CASES],
)
def test_sync_job_get_wraps_param_serialization_errors(
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
def test_sync_job_get_preserves_hyperbrowser_serialization_errors(
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
def test_sync_job_get_rejects_non_dict_serialized_params(
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
def test_async_job_get_wraps_param_serialization_errors(
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
def test_async_job_get_preserves_hyperbrowser_serialization_errors(
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
def test_async_job_get_rejects_non_dict_serialized_params(
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
