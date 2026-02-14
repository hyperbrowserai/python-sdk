import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.computer_action_request_utils as request_utils


def test_execute_computer_action_request_posts_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, endpoint, data=None):
            captured["endpoint"] = endpoint
            captured["data"] = data
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _SyncTransport()

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = request_utils.parse_response_model
    request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = request_utils.execute_computer_action_request(
            client=_Client(),
            endpoint="https://example.com/cua",
            payload={"action": {"type": "screenshot"}},
            operation_name="computer action",
        )
    finally:
        request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["endpoint"] == "https://example.com/cua"
    assert captured["data"] == {"action": {"type": "screenshot"}}
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "computer action"


def test_execute_computer_action_request_async_posts_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, endpoint, data=None):
            captured["endpoint"] = endpoint
            captured["data"] = data
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _AsyncTransport()

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = request_utils.parse_response_model
    request_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            request_utils.execute_computer_action_request_async(
                client=_Client(),
                endpoint="https://example.com/cua",
                payload={"action": {"type": "screenshot"}},
                operation_name="computer action",
            )
        )
    finally:
        request_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["endpoint"] == "https://example.com/cua"
    assert captured["data"] == {"action": {"type": "screenshot"}}
    assert captured["parse_data"] == {"success": True}
    assert captured["parse_kwargs"]["operation_name"] == "computer action"
