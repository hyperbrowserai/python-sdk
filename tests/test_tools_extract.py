import asyncio

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


def test_extract_tool_runnable_preserves_hyperbrowser_schema_parse_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_hyperbrowser_error(_: str):
        raise HyperbrowserError("custom schema parse failure")

    monkeypatch.setattr(tools_module.json, "loads", _raise_hyperbrowser_error)

    with pytest.raises(HyperbrowserError, match="custom schema parse failure") as exc_info:
        WebsiteExtractTool.runnable(
            _SyncClient(),
            {
                "urls": ["https://example.com"],
                "schema": '{"type":"object"}',
            },
        )

    assert exc_info.value.original_error is None
