import asyncio
from io import BytesIO

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

    def _fake_get_model_response_data(**kwargs):
        captured.update(kwargs)
        return {"extensions": []}

    def _fake_parse_extension_list_response_data(data):
        captured["parse_data"] = data
        return ["parsed"]

    original_get_data = extension_request_utils.get_model_response_data
    original_parse = extension_request_utils.parse_extension_list_response_data
    extension_request_utils.get_model_response_data = _fake_get_model_response_data
    extension_request_utils.parse_extension_list_response_data = (
        _fake_parse_extension_list_response_data
    )
    try:
        result = extension_request_utils.list_extension_resources(
            client=object(),
            route_path="/extensions/list",
        )
    finally:
        extension_request_utils.get_model_response_data = original_get_data
        extension_request_utils.parse_extension_list_response_data = original_parse

    assert result == ["parsed"]
    assert captured["route_path"] == "/extensions/list"
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

    async def _fake_get_model_response_data_async(**kwargs):
        captured.update(kwargs)
        return {"extensions": []}

    def _fake_parse_extension_list_response_data(data):
        captured["parse_data"] = data
        return ["parsed"]

    original_get_data = extension_request_utils.get_model_response_data_async
    original_parse = extension_request_utils.parse_extension_list_response_data
    extension_request_utils.get_model_response_data_async = (
        _fake_get_model_response_data_async
    )
    extension_request_utils.parse_extension_list_response_data = (
        _fake_parse_extension_list_response_data
    )
    try:
        result = asyncio.run(
            extension_request_utils.list_extension_resources_async(
                client=object(),
                route_path="/extensions/list",
            )
        )
    finally:
        extension_request_utils.get_model_response_data_async = original_get_data
        extension_request_utils.parse_extension_list_response_data = original_parse

    assert result == ["parsed"]
    assert captured["route_path"] == "/extensions/list"
    assert captured["parse_data"] == {"extensions": []}
