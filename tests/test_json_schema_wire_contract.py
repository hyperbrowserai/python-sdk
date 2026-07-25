from copy import deepcopy

import pytest
from pydantic import BaseModel

from hyperbrowser.client.managers.async_manager.agents.browser_use import (
    BrowserUseManager as AsyncBrowserUseManager,
)
from hyperbrowser.client.managers.async_manager.extract import (
    ExtractManager as AsyncExtractManager,
)
from hyperbrowser.client.managers.async_manager.web import (
    WebManager as AsyncWebManager,
)
from hyperbrowser.client.managers.sync_manager.agents.browser_use import (
    BrowserUseManager,
)
from hyperbrowser.client.managers.sync_manager.extract import ExtractManager
from hyperbrowser.client.managers.sync_manager.web import WebManager
from hyperbrowser.models import StartBrowserUseTaskParams


RAW_SCHEMA = {
    "$defs": {
        "snake_case_name": {
            "type": "object",
            "properties": {
                "keep_this_name": {
                    "type": ["string", "null"],
                    "default": None,
                }
            },
        }
    },
    "$ref": "#/$defs/snake_case_name",
    "x-custom-keyword": {"camelCase": None},
}


class StubResponse:
    def __init__(self, data):
        self.data = data


class RecordingSyncTransport:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, files=None):
        self.calls.append({"url": url, "data": data, "files": files})
        if url.endswith("/extract"):
            return StubResponse({"jobId": "extract_123"})
        if url.endswith("/task/browser-use"):
            return StubResponse({"jobId": "task_123"})
        if url.endswith("/web/fetch"):
            return StubResponse({"jobId": "fetch_123", "status": "pending"})
        raise AssertionError(f"Unexpected URL: {url}")


class RecordingAsyncTransport:
    def __init__(self):
        self.calls = []

    async def post(self, url, data=None, files=None):
        self.calls.append({"url": url, "data": data, "files": files})
        if url.endswith("/extract"):
            return StubResponse({"jobId": "extract_123"})
        if url.endswith("/task/browser-use"):
            return StubResponse({"jobId": "task_123"})
        if url.endswith("/web/fetch"):
            return StubResponse({"jobId": "fetch_123", "status": "pending"})
        raise AssertionError(f"Unexpected URL: {url}")


class FakeSyncClient:
    def __init__(self):
        self.transport = RecordingSyncTransport()

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


class FakeAsyncClient:
    def __init__(self):
        self.transport = RecordingAsyncTransport()

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


def _call_sync_schema_managers(client):
    ExtractManager(client).start(
        {
            "urls": ["https://example.com"],
            "schema": RAW_SCHEMA,
        }
    )
    BrowserUseManager(client).start(
        {
            "task": "Extract the page",
            "output_model_schema": RAW_SCHEMA,
        }
    )
    WebManager(client).fetch(
        {
            "url": "https://example.com",
            "outputs": {
                "formats": [
                    {
                        "type": "json",
                        "schema": RAW_SCHEMA,
                    }
                ]
            },
        }
    )


async def _call_async_schema_managers(client):
    await AsyncExtractManager(client).start(
        {
            "urls": ["https://example.com"],
            "schema": RAW_SCHEMA,
        }
    )
    await AsyncBrowserUseManager(client).start(
        {
            "task": "Extract the page",
            "output_model_schema": RAW_SCHEMA,
        }
    )
    await AsyncWebManager(client).fetch(
        {
            "url": "https://example.com",
            "outputs": {
                "formats": [
                    {
                        "type": "json",
                        "schema": RAW_SCHEMA,
                    }
                ]
            },
        }
    )


def _assert_raw_schema_calls(calls):
    assert calls[0]["data"]["schema"] == RAW_SCHEMA
    assert calls[1]["data"]["outputModelSchema"] == RAW_SCHEMA
    assert calls[2]["data"]["outputs"]["formats"][0]["schema"] == RAW_SCHEMA


def test_sync_managers_preserve_raw_json_schemas():
    original = deepcopy(RAW_SCHEMA)
    client = FakeSyncClient()

    _call_sync_schema_managers(client)

    _assert_raw_schema_calls(client.transport.calls)
    assert RAW_SCHEMA == original


@pytest.mark.anyio
async def test_async_managers_preserve_raw_json_schemas():
    original = deepcopy(RAW_SCHEMA)
    client = FakeAsyncClient()

    await _call_async_schema_managers(client)

    _assert_raw_schema_calls(client.transport.calls)
    assert RAW_SCHEMA == original


def test_legacy_request_model_is_not_mutated_when_schema_is_generated():
    class Address(BaseModel):
        postal_code: str

    class Person(BaseModel):
        address: Address

    params = StartBrowserUseTaskParams(
        task="Extract the page",
        output_model_schema=Person,
    )
    client = FakeSyncClient()

    BrowserUseManager(client).start(params)

    assert params.output_model_schema is Person
    schema = client.transport.calls[0]["data"]["outputModelSchema"]
    assert "$ref" not in schema["properties"]["address"]
    assert schema["properties"]["address"]["properties"]["postal_code"]["type"] == (
        "string"
    )


def test_boolean_json_schemas_remain_valid_for_unconstrained_schema_fields():
    client = FakeSyncClient()

    ExtractManager(client).start(
        {
            "urls": ["https://example.com"],
            "schema": True,
        }
    )
    WebManager(client).fetch(
        {
            "url": "https://example.com",
            "outputs": {
                "formats": [
                    {
                        "type": "json",
                        "schema": False,
                    }
                ]
            },
        }
    )

    assert client.transport.calls[0]["data"]["schema"] is True
    assert client.transport.calls[1]["data"]["outputs"]["formats"][0]["schema"] is False
