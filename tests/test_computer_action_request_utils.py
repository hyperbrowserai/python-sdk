import asyncio

import hyperbrowser.client.managers.computer_action_request_utils as request_utils


def test_execute_computer_action_request_delegates_to_endpoint_post_helper():
    captured = {}

    def _fake_post_model_request_to_endpoint(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = request_utils.post_model_request_to_endpoint
    request_utils.post_model_request_to_endpoint = _fake_post_model_request_to_endpoint
    try:
        result = request_utils.execute_computer_action_request(
            client=object(),
            endpoint="https://example.com/cua",
            payload={"action": {"type": "screenshot"}},
            operation_name="computer action",
        )
    finally:
        request_utils.post_model_request_to_endpoint = original

    assert result == {"parsed": True}
    assert captured["endpoint"] == "https://example.com/cua"
    assert captured["data"] == {"action": {"type": "screenshot"}}
    assert captured["operation_name"] == "computer action"


def test_execute_computer_action_request_async_delegates_to_endpoint_post_helper():
    captured = {}

    async def _fake_post_model_request_to_endpoint_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original = request_utils.post_model_request_to_endpoint_async
    request_utils.post_model_request_to_endpoint_async = (
        _fake_post_model_request_to_endpoint_async
    )
    try:
        result = asyncio.run(
            request_utils.execute_computer_action_request_async(
                client=object(),
                endpoint="https://example.com/cua",
                payload={"action": {"type": "screenshot"}},
                operation_name="computer action",
            )
        )
    finally:
        request_utils.post_model_request_to_endpoint_async = original

    assert result == {"parsed": True}
    assert captured["endpoint"] == "https://example.com/cua"
    assert captured["data"] == {"action": {"type": "screenshot"}}
    assert captured["operation_name"] == "computer action"
