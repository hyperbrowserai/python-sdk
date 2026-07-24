import threading
from collections.abc import Mapping
from copy import deepcopy

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    PrivateAttr,
    field_serializer,
    field_validator,
)

from hyperbrowser.client.managers.async_manager.agents.browser_use import (
    BrowserUseManager as AsyncBrowserUseManager,
)
from hyperbrowser.client.managers.async_manager.extension import (
    ExtensionManager as AsyncExtensionManager,
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
from hyperbrowser.client.managers.sync_manager.extension import ExtensionManager
from hyperbrowser.client.managers.sync_manager.extract import ExtractManager
from hyperbrowser.client.managers.sync_manager.scrape import ScrapeManager
from hyperbrowser.client.managers.sync_manager.web import WebManager
from hyperbrowser.models import (
    CreateExtensionParams,
    FetchOutputJson,
    FetchOutputOptions,
    FetchParams,
    StartBrowserUseTaskParams,
    StartBatchFetchJobParams,
    StartScrapeJobParams,
    StartWebCrawlJobParams,
)


class StubResponse:
    def __init__(self, data):
        self.data = data


class RecordingSyncTransport:
    def __init__(self):
        self.calls = []
        self.extension_file = None
        self.extension_file_was_open = None

    def post(self, url, data=None, files=None):
        self.calls.append({"url": url, "data": data, "files": files})
        if url.endswith("/scrape"):
            return StubResponse({"jobId": "scrape_123"})
        if url.endswith("/extract"):
            return StubResponse({"jobId": "extract_123"})
        if url.endswith("/web/fetch"):
            return StubResponse({"jobId": "fetch_123", "status": "pending"})
        if url.endswith("/web/batch-fetch"):
            return StubResponse({"jobId": "batch_fetch_123"})
        if url.endswith("/web/crawl"):
            return StubResponse({"jobId": "crawl_123"})
        if url.endswith("/task/browser-use"):
            return StubResponse({"jobId": "browser_use_123"})
        if url.endswith("/extensions/add"):
            self.extension_file = files["file"]
            self.extension_file_was_open = not self.extension_file.closed
            return StubResponse(
                {
                    "id": "extension_123",
                    "name": data["name"],
                    "createdAt": "2026-07-23T00:00:00Z",
                    "updatedAt": "2026-07-23T00:00:00Z",
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")


class RecordingAsyncTransport:
    def __init__(self):
        self.calls = []
        self.extension_file = None
        self.extension_file_was_open = None

    async def post(self, url, data=None, files=None):
        self.calls.append({"url": url, "data": data, "files": files})
        if url.endswith("/extract"):
            return StubResponse({"jobId": "extract_123"})
        if url.endswith("/web/fetch"):
            return StubResponse({"jobId": "fetch_123", "status": "pending"})
        if url.endswith("/web/batch-fetch"):
            return StubResponse({"jobId": "batch_fetch_123"})
        if url.endswith("/web/crawl"):
            return StubResponse({"jobId": "crawl_123"})
        if url.endswith("/task/browser-use"):
            return StubResponse({"jobId": "browser_use_123"})
        if url.endswith("/extensions/add"):
            self.extension_file = files["file"]
            self.extension_file_was_open = not self.extension_file.closed
            return StubResponse(
                {
                    "id": "extension_123",
                    "name": data["name"],
                    "createdAt": "2026-07-23T00:00:00Z",
                    "updatedAt": "2026-07-23T00:00:00Z",
                }
            )
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


def test_legacy_request_subclass_with_noncopyable_private_state_still_serializes():
    class LockedScrapeParams(StartScrapeJobParams):
        _lock = PrivateAttr(default_factory=threading.Lock)

    params = LockedScrapeParams(url="https://example.com")
    lock = params._lock
    client = FakeSyncClient()

    response = ScrapeManager(client).start(params)

    assert response.job_id == "scrape_123"
    assert params._lock is lock
    assert client.transport.calls[0]["data"] == {
        "url": "https://example.com",
    }


def test_schema_normalization_preserves_legacy_subclass_field_serializers():
    class Product(BaseModel):
        product_name: str

    class SerializedBrowserUseParams(StartBrowserUseTaskParams):
        model_config = ConfigDict(validate_assignment=True)

        _lock = PrivateAttr(default_factory=threading.Lock)

        @field_validator("output_model_schema", mode="before")
        @classmethod
        def validate_generated_schema(cls, schema):
            if isinstance(schema, dict):
                return {"assignment_validated": schema}
            return schema

        @field_serializer("output_model_schema")
        def serialize_output_model_schema(self, schema):
            assert not hasattr(schema, "model_json_schema")
            return {"serialized_schema": schema}

    class AssignmentValidatedFetchOutput(FetchOutputJson):
        model_config = ConfigDict(validate_assignment=True)

        @field_validator("schema_", mode="before")
        @classmethod
        def validate_generated_schema(cls, schema):
            if isinstance(schema, dict):
                return {"assignment_validated": schema}
            return schema

    class SerializedFetchParams(FetchParams):
        @field_serializer("outputs")
        def serialize_outputs(self, outputs):
            schema = outputs.formats[0].schema_
            assert not hasattr(schema, "model_json_schema")
            return {
                "formats": [
                    {
                        "type": "json",
                        "schema": {"serialized_schema": schema},
                    }
                ]
            }

    browser_params = SerializedBrowserUseParams(
        task="Extract the product",
        output_model_schema=Product,
    )
    fetch_output = AssignmentValidatedFetchOutput(type="json", schema=Product)
    fetch_params = SerializedFetchParams(
        url="https://example.com",
        outputs=FetchOutputOptions(formats=[fetch_output]),
    )
    browser_lock = browser_params._lock
    client = FakeSyncClient()

    BrowserUseManager(client).start(browser_params)
    WebManager(client).fetch(fetch_params)

    browser_schema = client.transport.calls[0]["data"]["outputModelSchema"][
        "serialized_schema"
    ]
    fetch_schema = client.transport.calls[1]["data"]["outputs"]["formats"][0]["schema"][
        "serialized_schema"
    ]
    assert (
        browser_schema["assignment_validated"]["properties"]["product_name"]["type"]
        == "string"
    )
    assert (
        fetch_schema["assignment_validated"]["properties"]["product_name"]["type"]
        == "string"
    )
    assert browser_params.output_model_schema is Product
    assert browser_params._lock is browser_lock
    assert fetch_output.schema_ is Product


def test_mapping_registered_legacy_subclass_keeps_its_serializer():
    class Product(BaseModel):
        product_name: str

    class MappingBrowserUseParams(StartBrowserUseTaskParams):
        @field_serializer("output_model_schema")
        def serialize_output_model_schema(self, schema):
            return {"serialized_schema": schema}

    Mapping.register(MappingBrowserUseParams)
    params = MappingBrowserUseParams(
        task="Extract the product",
        output_model_schema=Product,
    )
    client = FakeSyncClient()

    BrowserUseManager(client).start(params)

    schema = client.transport.calls[0]["data"]["outputModelSchema"]["serialized_schema"]
    assert schema["properties"]["product_name"]["type"] == "string"
    assert params.output_model_schema is Product


def test_nested_legacy_schema_models_are_normalized_without_mutating_callers():
    class Address(BaseModel):
        postal_code: str

    class Person(BaseModel):
        address: Address

    nested_output = FetchOutputJson(type="json", schema=Person)
    legacy_params = FetchParams(
        url="https://example.com/legacy",
        outputs=FetchOutputOptions(formats=[nested_output]),
    )
    batch_nested_output = FetchOutputJson(type="json", schema=Person)
    batch_params = StartBatchFetchJobParams(
        urls=["https://example.com/batch"],
        outputs=FetchOutputOptions(formats=[batch_nested_output]),
    )
    crawl_nested_output = FetchOutputJson(type="json", schema=Person)
    crawl_params = StartWebCrawlJobParams(
        url="https://example.com/crawl",
        outputs=FetchOutputOptions(formats=[crawl_nested_output]),
    )
    mixed_nested_output = FetchOutputJson(type="json", schema=Person)
    mixed_params = {
        "url": "https://example.com/mixed",
        "outputs": {"formats": [mixed_nested_output]},
    }
    client = FakeSyncClient()

    WebManager(client).fetch(legacy_params)
    WebManager(client).batch_fetch.start(batch_params)
    WebManager(client).crawl.start(crawl_params)
    WebManager(client).fetch(mixed_params)

    assert legacy_params.outputs is not None
    assert legacy_params.outputs.formats is not None
    assert legacy_params.outputs.formats[0] is nested_output
    for output in (
        nested_output,
        batch_nested_output,
        crawl_nested_output,
        mixed_nested_output,
    ):
        assert output.schema_ is Person

    for call in client.transport.calls:
        schema = call["data"]["outputs"]["formats"][0]["schema"]
        assert "$ref" not in schema["properties"]["address"]
        assert schema["properties"]["address"]["properties"]["postal_code"]["type"] == (
            "string"
        )


class StructuralSchemaProvider:
    @classmethod
    def model_json_schema(cls):
        return {
            "$defs": {
                "Result": {
                    "type": "object",
                    "properties": {"snake_case": {"type": "string"}},
                }
            },
            "$ref": "#/$defs/Result",
        }


def test_sync_browser_use_accepts_structural_schema_provider_without_mutation():
    params = {
        "task": "Extract the page",
        "output_model_schema": StructuralSchemaProvider,
    }
    original = dict(params)
    client = FakeSyncClient()

    response = BrowserUseManager(client).start(params)

    assert response.job_id == "browser_use_123"
    assert params == original
    assert params["output_model_schema"] is StructuralSchemaProvider
    schema = client.transport.calls[0]["data"]["outputModelSchema"]
    assert "$defs" not in schema
    assert schema == {
        "type": "object",
        "properties": {"snake_case": {"type": "string"}},
    }


@pytest.mark.anyio
async def test_async_browser_use_accepts_structural_schema_provider_without_mutation():
    params = {
        "task": "Extract the page",
        "output_model_schema": StructuralSchemaProvider,
    }
    original = dict(params)
    client = FakeAsyncClient()

    response = await AsyncBrowserUseManager(client).start(params)

    assert response.job_id == "browser_use_123"
    assert params == original
    assert params["output_model_schema"] is StructuralSchemaProvider
    schema = client.transport.calls[0]["data"]["outputModelSchema"]
    assert "$defs" not in schema
    assert schema == {
        "type": "object",
        "properties": {"snake_case": {"type": "string"}},
    }


@pytest.mark.anyio
async def test_async_nested_schema_models_are_normalized_without_mutating_callers():
    class Address(BaseModel):
        postal_code: str

    class Person(BaseModel):
        address: Address

    fetch_output = FetchOutputJson(type="json", schema=Person)
    fetch_params = FetchParams(
        url="https://example.com/fetch",
        outputs=FetchOutputOptions(formats=[fetch_output]),
    )
    batch_output = FetchOutputJson(type="json", schema=Person)
    batch_params = StartBatchFetchJobParams(
        urls=["https://example.com/batch"],
        outputs=FetchOutputOptions(formats=[batch_output]),
    )
    crawl_output = FetchOutputJson(type="json", schema=Person)
    crawl_params = StartWebCrawlJobParams(
        url="https://example.com/crawl",
        outputs=FetchOutputOptions(formats=[crawl_output]),
    )
    client = FakeAsyncClient()
    manager = AsyncWebManager(client)

    await manager.fetch(fetch_params)
    await manager.batch_fetch.start(batch_params)
    await manager.crawl.start(crawl_params)

    for output in (fetch_output, batch_output, crawl_output):
        assert output.schema_ is Person

    for call in client.transport.calls:
        schema = call["data"]["outputs"]["formats"][0]["schema"]
        assert "$ref" not in schema["properties"]["address"]
        assert schema["properties"]["address"]["properties"]["postal_code"]["type"] == (
            "string"
        )


@pytest.mark.parametrize("schema", [{}, False])
def test_sync_extract_accepts_empty_and_false_json_schemas(schema):
    params = {
        "urls": ["https://example.com"],
        "schema": schema,
    }
    original = deepcopy(params)
    client = FakeSyncClient()

    response = ExtractManager(client).start(params)

    assert response.job_id == "extract_123"
    assert client.transport.calls[0]["data"]["schema"] == schema
    assert params == original


@pytest.mark.anyio
@pytest.mark.parametrize("schema", [{}, False])
async def test_async_extract_accepts_empty_and_false_json_schemas(schema):
    params = {
        "urls": ["https://example.com"],
        "schema": schema,
    }
    original = deepcopy(params)
    client = FakeAsyncClient()

    response = await AsyncExtractManager(client).start(params)

    assert response.job_id == "extract_123"
    assert client.transport.calls[0]["data"]["schema"] == schema
    assert params == original


def test_sync_extension_keeps_legacy_model_unchanged_and_closes_file(tmp_path):
    archive = tmp_path / "extension.zip"
    archive.write_bytes(b"extension")
    params = CreateExtensionParams(name="Example", file_path=str(archive))
    before = params.model_dump()
    client = FakeSyncClient()

    response = ExtensionManager(client).create(params)

    assert response.id == "extension_123"
    assert params.model_dump() == before
    assert client.transport.calls[0]["data"] == {"name": "Example"}
    assert client.transport.extension_file_was_open is True
    assert client.transport.extension_file.closed


@pytest.mark.anyio
async def test_async_extension_keeps_legacy_model_unchanged_and_closes_file(tmp_path):
    archive = tmp_path / "extension.zip"
    archive.write_bytes(b"extension")
    params = CreateExtensionParams(name="Example", file_path=str(archive))
    before = params.model_dump()
    client = FakeAsyncClient()

    response = await AsyncExtensionManager(client).create(params)

    assert response.id == "extension_123"
    assert params.model_dump() == before
    assert client.transport.calls[0]["data"] == {"name": "Example"}
    assert client.transport.extension_file_was_open is True
    assert client.transport.extension_file.closed
