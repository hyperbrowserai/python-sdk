import asyncio
from io import BytesIO
from types import SimpleNamespace

import hyperbrowser.client.managers.extension_request_utils as extension_request_utils


def test_create_extension_resource_uses_post_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data=None, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"id": "ext_1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = extension_request_utils.parse_response_model
    extension_request_utils.parse_response_model = _fake_parse_response_model
    try:
        file_stream = BytesIO(b"ext")
        result = extension_request_utils.create_extension_resource(
            client=_Client(),
            route_path="/extensions/add",
            payload={"name": "ext"},
            file_stream=file_stream,
            model=object,
            operation_name="create extension",
        )
    finally:
        extension_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/extensions/add"
    assert captured["data"] == {"name": "ext"}
    assert captured["files"] == {"file": file_stream}
    assert captured["parse_data"] == {"id": "ext_1"}
    assert captured["parse_kwargs"]["operation_name"] == "create extension"


def test_list_extension_resources_uses_get_and_extension_parser():
    captured = {}

    class _SyncTransport:
        def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"extensions": []})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_extension_list_response_data(data):
        captured["parse_data"] = data
        return ["parsed"]

    original_parse = extension_request_utils.parse_extension_list_response_data
    extension_request_utils.parse_extension_list_response_data = (
        _fake_parse_extension_list_response_data
    )
    try:
        result = extension_request_utils.list_extension_resources(
            client=_Client(),
            route_path="/extensions/list",
        )
    finally:
        extension_request_utils.parse_extension_list_response_data = original_parse

    assert result == ["parsed"]
    assert captured["url"] == "https://api.example.test/extensions/list"
    assert captured["parse_data"] == {"extensions": []}


def test_create_extension_resource_async_uses_post_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data=None, files=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return SimpleNamespace(data={"id": "ext_2"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = extension_request_utils.parse_response_model
    extension_request_utils.parse_response_model = _fake_parse_response_model
    try:
        file_stream = BytesIO(b"ext")
        result = asyncio.run(
            extension_request_utils.create_extension_resource_async(
                client=_Client(),
                route_path="/extensions/add",
                payload={"name": "ext"},
                file_stream=file_stream,
                model=object,
                operation_name="create extension",
            )
        )
    finally:
        extension_request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/extensions/add"
    assert captured["data"] == {"name": "ext"}
    assert captured["files"] == {"file": file_stream}
    assert captured["parse_data"] == {"id": "ext_2"}
    assert captured["parse_kwargs"]["operation_name"] == "create extension"


def test_list_extension_resources_async_uses_get_and_extension_parser():
    captured = {}

    class _AsyncTransport:
        async def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"extensions": []})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_extension_list_response_data(data):
        captured["parse_data"] = data
        return ["parsed"]

    original_parse = extension_request_utils.parse_extension_list_response_data
    extension_request_utils.parse_extension_list_response_data = (
        _fake_parse_extension_list_response_data
    )
    try:
        result = asyncio.run(
            extension_request_utils.list_extension_resources_async(
                client=_Client(),
                route_path="/extensions/list",
            )
        )
    finally:
        extension_request_utils.parse_extension_list_response_data = original_parse

    assert result == ["parsed"]
    assert captured["url"] == "https://api.example.test/extensions/list"
    assert captured["parse_data"] == {"extensions": []}
