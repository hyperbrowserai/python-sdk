import asyncio
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.tools import (
    BrowserUseTool,
    WebsiteCrawlTool,
    WebsiteScrapeTool,
    WebsiteScreenshotTool,
)


class _Response:
    def __init__(self, data: Any = None, *, data_error: Optional[Exception] = None):
        self._data = data
        self._data_error = data_error

    @property
    def data(self) -> Any:
        if self._data_error is not None:
            raise self._data_error
        return self._data


class _SyncScrapeManager:
    def __init__(self, response: _Response):
        self._response = response

    def start_and_wait(self, params: object) -> _Response:
        _ = params
        return self._response


class _AsyncScrapeManager:
    def __init__(self, response: _Response):
        self._response = response

    async def start_and_wait(self, params: object) -> _Response:
        _ = params
        return self._response


class _SyncCrawlManager:
    def __init__(self, response: _Response):
        self._response = response

    def start_and_wait(self, params: object) -> _Response:
        _ = params
        return self._response


class _AsyncCrawlManager:
    def __init__(self, response: _Response):
        self._response = response

    async def start_and_wait(self, params: object) -> _Response:
        _ = params
        return self._response


class _SyncBrowserUseManager:
    def __init__(self, response: _Response):
        self._response = response

    def start_and_wait(self, params: object) -> _Response:
        _ = params
        return self._response


class _AsyncBrowserUseManager:
    def __init__(self, response: _Response):
        self._response = response

    async def start_and_wait(self, params: object) -> _Response:
        _ = params
        return self._response


class _SyncScrapeClient:
    def __init__(self, response: _Response):
        self.scrape = _SyncScrapeManager(response)


class _AsyncScrapeClient:
    def __init__(self, response: _Response):
        self.scrape = _AsyncScrapeManager(response)


class _SyncCrawlClient:
    def __init__(self, response: _Response):
        self.crawl = _SyncCrawlManager(response)


class _AsyncCrawlClient:
    def __init__(self, response: _Response):
        self.crawl = _AsyncCrawlManager(response)


class _SyncBrowserUseClient:
    def __init__(self, response: _Response):
        self.agents = SimpleNamespace(
            browser_use=_SyncBrowserUseManager(response),
        )


class _AsyncBrowserUseClient:
    def __init__(self, response: _Response):
        self.agents = SimpleNamespace(
            browser_use=_AsyncBrowserUseManager(response),
        )


def test_scrape_tool_wraps_response_data_read_failures():
    client = _SyncScrapeClient(
        _Response(data_error=RuntimeError("broken response data"))
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to read scrape tool response data"
    ) as exc_info:
        WebsiteScrapeTool.runnable(client, {"url": "https://example.com"})

    assert exc_info.value.original_error is not None


def test_scrape_tool_preserves_hyperbrowser_response_data_read_failures():
    client = _SyncScrapeClient(
        _Response(data_error=HyperbrowserError("custom scrape data failure"))
    )

    with pytest.raises(
        HyperbrowserError, match="custom scrape data failure"
    ) as exc_info:
        WebsiteScrapeTool.runnable(client, {"url": "https://example.com"})

    assert exc_info.value.original_error is None


def test_scrape_tool_rejects_non_string_markdown_field():
    client = _SyncScrapeClient(_Response(data=SimpleNamespace(markdown=123)))

    with pytest.raises(
        HyperbrowserError,
        match="scrape tool response field 'markdown' must be a string",
    ):
        WebsiteScrapeTool.runnable(client, {"url": "https://example.com"})


def test_screenshot_tool_rejects_non_string_screenshot_field():
    client = _SyncScrapeClient(_Response(data=SimpleNamespace(screenshot=123)))

    with pytest.raises(
        HyperbrowserError,
        match="screenshot tool response field 'screenshot' must be a string",
    ):
        WebsiteScreenshotTool.runnable(client, {"url": "https://example.com"})


def test_crawl_tool_rejects_non_list_response_data():
    client = _SyncCrawlClient(_Response(data={"invalid": "payload"}))

    with pytest.raises(
        HyperbrowserError, match="crawl tool response data must be a list"
    ):
        WebsiteCrawlTool.runnable(client, {"url": "https://example.com"})


def test_crawl_tool_wraps_page_field_read_failures():
    class _BrokenPage:
        @property
        def markdown(self) -> str:
            raise RuntimeError("cannot read markdown")

    client = _SyncCrawlClient(_Response(data=[_BrokenPage()]))

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read crawl tool page field 'markdown' at index 0",
    ) as exc_info:
        WebsiteCrawlTool.runnable(client, {"url": "https://example.com"})

    assert exc_info.value.original_error is not None


def test_crawl_tool_rejects_non_string_page_urls():
    client = _SyncCrawlClient(
        _Response(data=[SimpleNamespace(url=42, markdown="body")])
    )

    with pytest.raises(
        HyperbrowserError,
        match="crawl tool page field 'url' must be a string at index 0",
    ):
        WebsiteCrawlTool.runnable(client, {"url": "https://example.com"})


def test_crawl_tool_uses_unknown_url_for_blank_page_urls():
    client = _SyncCrawlClient(
        _Response(data=[SimpleNamespace(url="   ", markdown="page body")])
    )

    output = WebsiteCrawlTool.runnable(client, {"url": "https://example.com"})

    assert "Url: <unknown url>" in output
    assert "page body" in output


def test_crawl_tool_wraps_response_iteration_failures():
    class _BrokenList(list):
        def __iter__(self):
            raise RuntimeError("cannot iterate pages")

    client = _SyncCrawlClient(_Response(data=_BrokenList([SimpleNamespace()])))

    with pytest.raises(
        HyperbrowserError, match="Failed to iterate crawl tool response data"
    ) as exc_info:
        WebsiteCrawlTool.runnable(client, {"url": "https://example.com"})

    assert exc_info.value.original_error is not None


def test_browser_use_tool_rejects_non_string_final_result():
    client = _SyncBrowserUseClient(_Response(data=SimpleNamespace(final_result=123)))

    with pytest.raises(
        HyperbrowserError,
        match="browser-use tool response field 'final_result' must be a string",
    ):
        BrowserUseTool.runnable(client, {"task": "search docs"})


def test_async_scrape_tool_wraps_response_data_read_failures():
    async def run() -> None:
        client = _AsyncScrapeClient(
            _Response(data_error=RuntimeError("broken async response data"))
        )
        with pytest.raises(
            HyperbrowserError, match="Failed to read scrape tool response data"
        ) as exc_info:
            await WebsiteScrapeTool.async_runnable(
                client,
                {"url": "https://example.com"},
            )
        assert exc_info.value.original_error is not None

    asyncio.run(run())


def test_async_crawl_tool_rejects_non_list_response_data():
    async def run() -> None:
        client = _AsyncCrawlClient(_Response(data={"invalid": "payload"}))
        with pytest.raises(
            HyperbrowserError, match="crawl tool response data must be a list"
        ):
            await WebsiteCrawlTool.async_runnable(
                client, {"url": "https://example.com"}
            )

    asyncio.run(run())


def test_async_browser_use_tool_rejects_non_string_final_result():
    async def run() -> None:
        client = _AsyncBrowserUseClient(
            _Response(data=SimpleNamespace(final_result=123))
        )
        with pytest.raises(
            HyperbrowserError,
            match="browser-use tool response field 'final_result' must be a string",
        ):
            await BrowserUseTool.async_runnable(client, {"task": "search docs"})

    asyncio.run(run())
