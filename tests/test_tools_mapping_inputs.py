from types import MappingProxyType

import asyncio
import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.scrape import StartScrapeJobParams
from hyperbrowser.tools import WebsiteExtractTool, WebsiteScrapeTool


class _Response:
    def __init__(self, data):
        self.data = data


class _ScrapeManager:
    def __init__(self):
        self.last_params = None

    def start_and_wait(self, params: StartScrapeJobParams):
        self.last_params = params
        return _Response(type("Data", (), {"markdown": "ok"})())


class _Client:
    def __init__(self):
        self.scrape = _ScrapeManager()


class _AsyncScrapeManager:
    async def start_and_wait(self, params: StartScrapeJobParams):
        return _Response(type("Data", (), {"markdown": "ok"})())


class _AsyncClient:
    def __init__(self):
        self.scrape = _AsyncScrapeManager()


def test_tool_wrappers_accept_mapping_inputs():
    client = _Client()
    params = MappingProxyType({"url": "https://example.com"})

    output = WebsiteScrapeTool.runnable(client, params)

    assert output == "ok"
    assert isinstance(client.scrape.last_params, StartScrapeJobParams)


def test_tool_wrappers_reject_non_mapping_inputs():
    client = _Client()

    with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
        WebsiteScrapeTool.runnable(client, ["https://example.com"])  # type: ignore[arg-type]


def test_extract_tool_wrapper_rejects_non_mapping_inputs():
    class _ExtractManager:
        def start_and_wait(self, params):
            return type("_Response", (), {"data": {"ok": True}})()

    class _ExtractClient:
        def __init__(self):
            self.extract = _ExtractManager()

    client = _ExtractClient()
    with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
        WebsiteExtractTool.runnable(client, "bad")  # type: ignore[arg-type]


def test_async_tool_wrappers_reject_non_mapping_inputs():
    async def run() -> None:
        client = _AsyncClient()
        with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
            await WebsiteScrapeTool.async_runnable(
                client,
                ["https://example.com"],  # type: ignore[arg-type]
            )

    asyncio.run(run())
