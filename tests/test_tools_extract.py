import asyncio

import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extract import StartExtractJobParams
from hyperbrowser.tools import WebsiteExtractTool


class _Response:
    def __init__(self, data):
        self.data = data


class _SyncExtractManager:
    def __init__(self):
        self.last_params = None

    def start_and_wait(self, params: StartExtractJobParams):
        self.last_params = params
        return _Response({"ok": True})


class _AsyncExtractManager:
    def __init__(self):
        self.last_params = None

    async def start_and_wait(self, params: StartExtractJobParams):
        self.last_params = params
        return _Response({"ok": True})


class _SyncClient:
    def __init__(self):
        self.extract = _SyncExtractManager()


class _AsyncClient:
    def __init__(self):
        self.extract = _AsyncExtractManager()


def test_extract_tool_runnable_does_not_mutate_input_params():
    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": '{"type":"object","properties":{"name":{"type":"string"}}}',
    }

    output = WebsiteExtractTool.runnable(client, params)

    assert output == '{"ok": true}'
    assert isinstance(client.extract.last_params, StartExtractJobParams)
    assert isinstance(client.extract.last_params.schema_, dict)
    assert params["schema"] == '{"type":"object","properties":{"name":{"type":"string"}}}'


def test_extract_tool_async_runnable_does_not_mutate_input_params():
    client = _AsyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": '{"type":"object","properties":{"name":{"type":"string"}}}',
    }

    async def run():
        return await WebsiteExtractTool.async_runnable(client, params)

    output = asyncio.run(run())

    assert output == '{"ok": true}'
    assert isinstance(client.extract.last_params, StartExtractJobParams)
    assert isinstance(client.extract.last_params.schema_, dict)
    assert params["schema"] == '{"type":"object","properties":{"name":{"type":"string"}}}'


def test_extract_tool_runnable_raises_for_invalid_schema_json():
    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": "{invalid-json}",
    }

    with pytest.raises(HyperbrowserError, match="Invalid JSON string provided for `schema`"):
        WebsiteExtractTool.runnable(client, params)
