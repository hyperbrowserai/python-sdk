import asyncio
from io import BytesIO
from types import SimpleNamespace

import hyperbrowser.client.managers.extension_request_utils as extension_request_utils


def test_create_extension_resource_delegates_to_post_model_request():
    captured = {}

    def _fake_post_model_request(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = extension_request_utils.post_model_request
    extension_request_utils.post_model_request = _fake_post_model_request
    try:
        file_stream = BytesIO(b"ext")
        result = extension_request_utils.create_extension_resource(
            client=object(),
            route_path="/extensions/add",
            payload={"name": "ext"},
            file_stream=file_stream,
            model=object,
            operation_name="create extension",
        )
    finally:
        extension_request_utils.post_model_request = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/extensions/add"
    assert captured["data"] == {"name": "ext"}
    assert captured["files"] == {"file": file_stream}
    assert captured["operation_name"] == "create extension"


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


def test_create_extension_resource_async_delegates_to_post_model_request_async():
    captured = {}

    async def _fake_post_model_request_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = extension_request_utils.post_model_request_async
    extension_request_utils.post_model_request_async = _fake_post_model_request_async
    try:
        file_stream = BytesIO(b"ext")
        result = asyncio.run(
            extension_request_utils.create_extension_resource_async(
                client=object(),
                route_path="/extensions/add",
                payload={"name": "ext"},
                file_stream=file_stream,
                model=object,
                operation_name="create extension",
            )
        )
    finally:
        extension_request_utils.post_model_request_async = original

    assert result == {"parsed": True}
    assert captured["route_path"] == "/extensions/add"
    assert captured["data"] == {"name": "ext"}
    assert captured["files"] == {"file": file_stream}
    assert captured["operation_name"] == "create extension"


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
