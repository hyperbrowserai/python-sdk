import asyncio
from collections.abc import Mapping
import math
from types import MappingProxyType

import pytest

import hyperbrowser.tools as tools_module
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extract import StartExtractJobParams
from hyperbrowser.tools import WebsiteExtractTool

_UNSET = object()


class _Response:
    def __init__(self, data):
        self.data = data


class _SyncExtractManager:
    def __init__(self, response_data=_UNSET):
        self.last_params = None
        self._response_data = {"ok": True} if response_data is _UNSET else response_data

    def start_and_wait(self, params: StartExtractJobParams):
        self.last_params = params
        return _Response(self._response_data)


class _AsyncExtractManager:
    def __init__(self, response_data=_UNSET):
        self.last_params = None
        self._response_data = {"ok": True} if response_data is _UNSET else response_data

    async def start_and_wait(self, params: StartExtractJobParams):
        self.last_params = params
        return _Response(self._response_data)


class _SyncClient:
    def __init__(self, response_data=_UNSET):
        self.extract = _SyncExtractManager(response_data=response_data)


class _AsyncClient:
    def __init__(self, response_data=_UNSET):
        self.extract = _AsyncExtractManager(response_data=response_data)


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
    assert (
        params["schema"] == '{"type":"object","properties":{"name":{"type":"string"}}}'
    )


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
    assert (
        params["schema"] == '{"type":"object","properties":{"name":{"type":"string"}}}'
    )


def test_extract_tool_runnable_raises_for_invalid_schema_json():
    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": "{invalid-json}",
    }

    with pytest.raises(
        HyperbrowserError, match="Invalid JSON string provided for `schema`"
    ):
        WebsiteExtractTool.runnable(client, params)


def test_extract_tool_async_runnable_raises_for_invalid_schema_json():
    client = _AsyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": "{invalid-json}",
    }

    async def run():
        await WebsiteExtractTool.async_runnable(client, params)

    with pytest.raises(
        HyperbrowserError, match="Invalid JSON string provided for `schema`"
    ):
        asyncio.run(run())


def test_extract_tool_runnable_rejects_non_object_schema_json():
    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": '["not-an-object"]',
    }

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` must decode to a JSON object"
    ):
        WebsiteExtractTool.runnable(client, params)


def test_extract_tool_async_runnable_rejects_non_object_schema_json():
    client = _AsyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": '["not-an-object"]',
    }

    async def run():
        await WebsiteExtractTool.async_runnable(client, params)

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` must decode to a JSON object"
    ):
        asyncio.run(run())


def test_extract_tool_runnable_rejects_non_mapping_non_string_schema():
    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": 123,
    }

    with pytest.raises(
        HyperbrowserError,
        match="Extract tool `schema` must be an object or JSON string",
    ):
        WebsiteExtractTool.runnable(client, params)


def test_extract_tool_async_runnable_rejects_non_mapping_non_string_schema():
    client = _AsyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": 123,
    }

    async def run():
        await WebsiteExtractTool.async_runnable(client, params)

    with pytest.raises(
        HyperbrowserError,
        match="Extract tool `schema` must be an object or JSON string",
    ):
        asyncio.run(run())


def test_extract_tool_runnable_rejects_string_subclass_schema_strings():
    class _SchemaString(str):
        pass

    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": _SchemaString('{"type":"object"}'),
    }

    with pytest.raises(
        HyperbrowserError,
        match="Extract tool `schema` must be an object or JSON string",
    ):
        WebsiteExtractTool.runnable(client, params)


def test_extract_tool_async_runnable_rejects_string_subclass_schema_strings():
    class _SchemaString(str):
        pass

    client = _AsyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": _SchemaString('{"type":"object"}'),
    }

    async def run():
        await WebsiteExtractTool.async_runnable(client, params)

    with pytest.raises(
        HyperbrowserError,
        match="Extract tool `schema` must be an object or JSON string",
    ):
        asyncio.run(run())


def test_extract_tool_runnable_rejects_null_schema_json():
    client = _SyncClient()
    params = {
        "urls": ["https://example.com"],
        "schema": "null",
    }

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` must decode to a JSON object"
    ):
        WebsiteExtractTool.runnable(client, params)


def test_extract_tool_runnable_normalizes_mapping_schema_values():
    client = _SyncClient()
    schema_mapping = MappingProxyType({"type": "object", "properties": {}})

    WebsiteExtractTool.runnable(
        client,
        {
            "urls": ["https://example.com"],
            "schema": schema_mapping,
        },
    )

    assert isinstance(client.extract.last_params, StartExtractJobParams)
    assert isinstance(client.extract.last_params.schema_, dict)
    assert client.extract.last_params.schema_ == {"type": "object", "properties": {}}


def test_extract_tool_async_runnable_normalizes_mapping_schema_values():
    client = _AsyncClient()
    schema_mapping = MappingProxyType({"type": "object", "properties": {}})

    async def run():
        return await WebsiteExtractTool.async_runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": schema_mapping,
            },
        )

    asyncio.run(run())

    assert isinstance(client.extract.last_params, StartExtractJobParams)
    assert isinstance(client.extract.last_params.schema_, dict)
    assert client.extract.last_params.schema_ == {"type": "object", "properties": {}}


def test_extract_tool_runnable_rejects_non_string_schema_keys():
    client = _SyncClient()

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` object keys must be strings"
    ):
        WebsiteExtractTool.runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": {1: "invalid-key"},  # type: ignore[dict-item]
            },
        )


def test_extract_tool_async_runnable_rejects_non_string_schema_keys():
    client = _AsyncClient()

    async def run():
        await WebsiteExtractTool.async_runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": {1: "invalid-key"},  # type: ignore[dict-item]
            },
        )

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` object keys must be strings"
    ):
        asyncio.run(run())


def test_extract_tool_runnable_rejects_string_subclass_schema_keys():
    class _SchemaKey(str):
        pass

    client = _SyncClient()

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` object keys must be strings"
    ):
        WebsiteExtractTool.runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": {_SchemaKey("type"): "object"},
            },
        )


def test_extract_tool_async_runnable_rejects_string_subclass_schema_keys():
    class _SchemaKey(str):
        pass

    client = _AsyncClient()

    async def run():
        await WebsiteExtractTool.async_runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": {_SchemaKey("type"): "object"},
            },
        )

    with pytest.raises(
        HyperbrowserError, match="Extract tool `schema` object keys must be strings"
    ):
        asyncio.run(run())


def test_extract_tool_runnable_wraps_schema_key_read_failures():
    class _BrokenSchemaMapping(Mapping[object, object]):
        def __iter__(self):
            raise RuntimeError("cannot iterate schema keys")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: object) -> object:
            return key

    client = _SyncClient()

    with pytest.raises(
        HyperbrowserError, match="Failed to read extract tool `schema` object keys"
    ) as exc_info:
        WebsiteExtractTool.runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": _BrokenSchemaMapping(),
            },
        )

    assert exc_info.value.original_error is not None


def test_extract_tool_async_runnable_wraps_schema_key_read_failures():
    class _BrokenSchemaMapping(Mapping[object, object]):
        def __iter__(self):
            raise RuntimeError("cannot iterate schema keys")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: object) -> object:
            return key

    client = _AsyncClient()

    async def run():
        await WebsiteExtractTool.async_runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": _BrokenSchemaMapping(),
            },
        )

    with pytest.raises(
        HyperbrowserError, match="Failed to read extract tool `schema` object keys"
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is not None


def test_extract_tool_runnable_wraps_schema_value_read_failures():
    class _BrokenSchemaMapping(Mapping[str, object]):
        def __iter__(self):
            yield "type"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read schema value")

    client = _SyncClient()

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read extract tool `schema` value for key 'type'",
    ) as exc_info:
        WebsiteExtractTool.runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": _BrokenSchemaMapping(),
            },
        )

    assert exc_info.value.original_error is not None


def test_extract_tool_async_runnable_wraps_schema_value_read_failures():
    class _BrokenSchemaMapping(Mapping[str, object]):
        def __iter__(self):
            yield "type"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read schema value")

    client = _AsyncClient()

    async def run():
        await WebsiteExtractTool.async_runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": _BrokenSchemaMapping(),
            },
        )

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read extract tool `schema` value for key 'type'",
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is not None


def test_extract_tool_runnable_preserves_hyperbrowser_schema_value_read_failures():
    class _BrokenSchemaMapping(Mapping[str, object]):
        def __iter__(self):
            yield "type"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise HyperbrowserError("custom schema value failure")

    client = _SyncClient()

    with pytest.raises(
        HyperbrowserError, match="custom schema value failure"
    ) as exc_info:
        WebsiteExtractTool.runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": _BrokenSchemaMapping(),
            },
        )

    assert exc_info.value.original_error is None


def test_extract_tool_async_runnable_preserves_hyperbrowser_schema_value_read_failures():
    class _BrokenSchemaMapping(Mapping[str, object]):
        def __iter__(self):
            yield "type"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise HyperbrowserError("custom schema value failure")

    client = _AsyncClient()

    async def run():
        await WebsiteExtractTool.async_runnable(
            client,
            {
                "urls": ["https://example.com"],
                "schema": _BrokenSchemaMapping(),
            },
        )

    with pytest.raises(
        HyperbrowserError, match="custom schema value failure"
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is None


def test_extract_tool_runnable_serializes_empty_object_data():
    client = _SyncClient(response_data={})

    output = WebsiteExtractTool.runnable(client, {"urls": ["https://example.com"]})

    assert output == "{}"


def test_extract_tool_async_runnable_serializes_empty_list_data():
    client = _AsyncClient(response_data=[])

    async def run():
        return await WebsiteExtractTool.async_runnable(
            client, {"urls": ["https://example.com"]}
        )

    output = asyncio.run(run())

    assert output == "[]"


def test_extract_tool_runnable_returns_empty_string_for_none_data():
    client = _SyncClient(response_data=None)

    output = WebsiteExtractTool.runnable(client, {"urls": ["https://example.com"]})

    assert output == ""


def test_extract_tool_runnable_wraps_serialization_failures():
    client = _SyncClient(response_data={1, 2})

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extract tool response data"
    ) as exc_info:
        WebsiteExtractTool.runnable(client, {"urls": ["https://example.com"]})

    assert exc_info.value.original_error is not None


def test_extract_tool_async_runnable_returns_empty_string_for_none_data():
    client = _AsyncClient(response_data=None)

    async def run():
        return await WebsiteExtractTool.async_runnable(
            client, {"urls": ["https://example.com"]}
        )

    output = asyncio.run(run())

    assert output == ""


def test_extract_tool_async_runnable_wraps_serialization_failures():
    client = _AsyncClient(response_data={1, 2})

    async def run():
        return await WebsiteExtractTool.async_runnable(
            client, {"urls": ["https://example.com"]}
        )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extract tool response data"
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is not None


def test_extract_tool_runnable_rejects_nan_json_payloads():
    client = _SyncClient(response_data={"value": math.nan})

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extract tool response data"
    ) as exc_info:
        WebsiteExtractTool.runnable(client, {"urls": ["https://example.com"]})

    assert exc_info.value.original_error is not None


def test_extract_tool_async_runnable_rejects_nan_json_payloads():
    client = _AsyncClient(response_data={"value": math.nan})

    async def run():
        return await WebsiteExtractTool.async_runnable(
            client, {"urls": ["https://example.com"]}
        )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extract tool response data"
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is not None


def test_extract_tool_runnable_wraps_unexpected_schema_parse_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_recursion_error(_: str):
        raise RecursionError("schema parsing recursion overflow")

    monkeypatch.setattr(tools_module.json, "loads", _raise_recursion_error)

    with pytest.raises(
        HyperbrowserError, match="Invalid JSON string provided for `schema`"
    ) as exc_info:
        WebsiteExtractTool.runnable(
            _SyncClient(),
            {
                "urls": ["https://example.com"],
                "schema": '{"type":"object"}',
            },
        )

    assert exc_info.value.original_error is not None


def test_extract_tool_async_runnable_wraps_unexpected_schema_parse_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_recursion_error(_: str):
        raise RecursionError("schema parsing recursion overflow")

    monkeypatch.setattr(tools_module.json, "loads", _raise_recursion_error)

    async def run():
        await WebsiteExtractTool.async_runnable(
            _AsyncClient(),
            {
                "urls": ["https://example.com"],
                "schema": '{"type":"object"}',
            },
        )

    with pytest.raises(
        HyperbrowserError, match="Invalid JSON string provided for `schema`"
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is not None


def test_extract_tool_runnable_preserves_hyperbrowser_schema_parse_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_hyperbrowser_error(_: str):
        raise HyperbrowserError("custom schema parse failure")

    monkeypatch.setattr(tools_module.json, "loads", _raise_hyperbrowser_error)

    with pytest.raises(
        HyperbrowserError, match="custom schema parse failure"
    ) as exc_info:
        WebsiteExtractTool.runnable(
            _SyncClient(),
            {
                "urls": ["https://example.com"],
                "schema": '{"type":"object"}',
            },
        )

    assert exc_info.value.original_error is None


def test_extract_tool_async_runnable_preserves_hyperbrowser_schema_parse_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_hyperbrowser_error(_: str):
        raise HyperbrowserError("custom schema parse failure")

    monkeypatch.setattr(tools_module.json, "loads", _raise_hyperbrowser_error)

    async def run():
        await WebsiteExtractTool.async_runnable(
            _AsyncClient(),
            {
                "urls": ["https://example.com"],
                "schema": '{"type":"object"}',
            },
        )

    with pytest.raises(
        HyperbrowserError, match="custom schema parse failure"
    ) as exc_info:
        asyncio.run(run())

    assert exc_info.value.original_error is None
