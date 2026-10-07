import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSessionParams,
    SessionLaunchState,
    WebMCPInvokeParams,
    WebMCPResultParams,
    WebMCPStartParams,
)

ID = "0123456789abcdef01234567"
HANDLE = {
    "invocationId": ID,
    "toolRef": "document-tool",
    "status": "running",
    "cancellationRequested": False,
    "createdAt": "2026-10-06T12:00:00Z",
}
RESULT = {
    "status": "completed",
    "output": {"snake_key": {"CamelKey": [None, 42]}},
    "outputBytes": 37,
    "untrustedContent": True,
    "durationMs": 12,
}


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def sdk(request):
    """Exercise the same wire contract through both public clients and transports."""
    is_async = request.param
    loop = asyncio.new_event_loop()
    client = (AsyncHyperbrowser if is_async else Hyperbrowser)(api_key="test-key")
    calls = []
    outcomes = []

    def handler(req):
        calls.append(req)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def call(method, *args, **kwargs):
        result = method(*args, **kwargs)
        return loop.run_until_complete(result) if is_async else result

    call(client.transport.close)
    client.transport.client = (httpx.AsyncClient if is_async else httpx.Client)(
        transport=httpx.MockTransport(handler),
        headers={"x-api-key": "test-key"},
        timeout=30,
    )
    if is_async:
        client.transport._closed = False
    yield client, call, calls, outcomes
    call(client.close)
    loop.close()


def respond(outcomes, payload, status=200):
    outcomes.append(httpx.Response(status, json=payload))


def test_session_opt_in_and_launch_state(sdk):
    client, call, calls, outcomes = sdk
    # Session creation defaults and legacy request behavior are covered by the
    # existing compatibility suite; this checks the new opt-in on the wire.
    for params in [
        {},
        {"enable_web_mcp": False},
        CreateSessionParams(enable_web_mcp=True),
    ]:
        respond(outcomes, {"message": "fixture stops before parsing"}, 400)
        with pytest.raises(HyperbrowserError):
            call(client.sessions.create, params)
    assert "enableWebMcp" not in json.loads(calls[0].content)
    assert json.loads(calls[1].content)["enableWebMcp"] is False
    assert json.loads(calls[2].content)["enableWebMcp"] is True
    assert SessionLaunchState(enableWebMcp=True).enable_web_mcp is True
    assert SessionLaunchState().enable_web_mcp is None


def test_discovery_metadata(sdk):
    client, call, calls, outcomes = sdk
    respond(
        outcomes,
        {
            "nativeSupported": True,
            "truncated": True,
            "tools": [
                {
                    "toolRef": "document-tool",
                    "name": "search",
                    "description": "Search",
                    "declarative": True,
                    "backendNodeId": 123,
                    "inputSchema": {"properties": {"user_query": {"type": "string"}}},
                    "outputSchema": {"type": "object"},
                    "annotations": {
                        "readOnly": True,
                        "untrustedContent": True,
                        "consequential": False,
                        "autosubmit": False,
                        "openWorld": True,
                    },
                    "source": {
                        "provider": "native",
                        "tabId": "tab",
                        "pageUrl": "https://page.test",
                        "pageTitle": "Page",
                        "frame": {
                            "id": "frame",
                            "url": "https://page.test/frame",
                            "isMainFrame": False,
                        },
                    },
                }
            ],
        },
    )
    result = call(client.sessions.webmcp.list_tools, "session /#")
    assert result.native_supported and result.truncated
    assert result.tools[0].backend_node_id == 123
    assert result.tools[0].input_schema["properties"]["user_query"] == {
        "type": "string"
    }
    assert result.tools[0].annotations.open_world
    assert not result.tools[0].source.frame.is_main_frame
    assert calls[0].url.raw_path == b"/api/session/session%20%2F%23/webmcp/tools"
    assert calls[0].extensions["timeout"]["read"] == 40
    assert calls[0].headers["x-api-key"] == "test-key"


@pytest.mark.parametrize("legacy", [False, True])
def test_invoke_request_parity_and_json_keys(sdk, legacy):
    client, call, calls, outcomes = sdk
    respond(outcomes, RESULT)
    params = {
        "tool_ref": "document-tool",
        "input": {"snake_key": {"CamelKey": None}},
        "timeout_seconds": 120,
    }
    result = call(
        client.sessions.webmcp.invoke,
        "s",
        WebMCPInvokeParams(**params) if legacy else params,
    )
    assert result.output == RESULT["output"]
    assert result.untrusted_content
    assert json.loads(calls[0].content) == {
        "toolRef": "document-tool",
        "input": params["input"],
        "timeoutSeconds": 120,
    }
    assert calls[0].extensions["timeout"]["read"] == 155
    assert client.transport.client.timeout.read == 30


@pytest.mark.parametrize("legacy", [False, True])
def test_start_poll_cancel_and_retention(sdk, legacy):
    client, call, calls, outcomes = sdk
    respond(outcomes, HANDLE, 202)
    respond(outcomes, {**HANDLE, "status": "awaiting_submission"})
    respond(
        outcomes,
        {
            **HANDLE,
            "status": "completed",
            "cancellationRequested": True,
            "result": RESULT,
            "expiresAt": "2026-10-06T12:10:00Z",
        },
    )
    start = {"tool_ref": "document-tool", "timeout_seconds": 3600}
    invocation = call(
        client.sessions.webmcp.start,
        "s",
        WebMCPStartParams(**start) if legacy else start,
    )
    assert invocation.status == "running"
    assert invocation.created_at == datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
    assert calls[-1].extensions["timeout"]["read"] == 40
    params = WebMCPResultParams(wait_seconds=30) if legacy else {"wait_seconds": 30}
    pending = call(
        client.sessions.webmcp.get_result, "s", invocation.invocation_id, params
    )
    assert pending.status == "awaiting_submission"
    assert dict(calls[-1].url.params) == {"waitSeconds": "30"}
    assert calls[-1].extensions["timeout"]["read"] == 50
    canceled = call(client.sessions.webmcp.cancel, "s", invocation.invocation_id)
    assert canceled.status == "completed"  # Completion can win cancellation.
    assert canceled.cancellation_requested
    assert canceled.result.output == RESULT["output"]
    assert canceled.expires_at is not None
    assert [(req.method, req.url.path) for req in calls] == [
        ("POST", "/api/session/s/webmcp/invocations"),
        ("GET", f"/api/session/s/webmcp/invocations/{ID}"),
        ("POST", f"/api/session/s/webmcp/invocations/{ID}/cancel"),
    ]


@pytest.mark.parametrize("method", ["invoke", "start", "cancel"])
@pytest.mark.parametrize("failure", ["network", "api"])
def test_mutations_never_retry_and_preserve_error_details(sdk, method, failure):
    client, call, calls, outcomes = sdk
    payload = {
        "code": "outcome_unknown",
        "message": "Unknown outcome",
        "invocationId": ID,
    }
    if failure == "network":
        outcomes.append(httpx.ReadError("socket lost"))
    else:
        respond(outcomes, payload, 504)
    args = ["s", ID if method == "cancel" else {"tool_ref": "t"}]
    with pytest.raises(HyperbrowserError) as raised:
        call(getattr(client.sessions.webmcp, method), *args)
    assert len(calls) == 1
    if failure == "api":
        assert raised.value.code == "outcome_unknown"
        assert raised.value.details == payload
        assert raised.value.status_code == 504


def test_missing_handle_is_not_retried(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, {"code": "invocation_not_found", "message": "Expired"}, 404)
    with pytest.raises(HyperbrowserError) as raised:
        call(client.sessions.webmcp.get_result, "s", ID)
    assert raised.value.code == "invocation_not_found"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {**RESULT, "output": None},
        {
            k: v
            for k, v in {
                **RESULT,
                "outputTruncated": True,
                "outputBytes": 2_000_000,
                "outputPreview": "preview",
            }.items()
            if k != "output"
        },
        {**RESULT, "status": "awaiting_submission", "invocationId": ID},
        {**RESULT, "status": "error", "errorText": "Page error"},
    ],
)
def test_result_shapes(sdk, payload):
    client, call, calls, outcomes = sdk
    respond(outcomes, payload)
    result = call(client.sessions.webmcp.invoke, "s", {"tool_ref": "t"})
    assert result.output == payload.get("output")
    assert result.status == payload["status"]
    assert result.output_truncated == payload.get("outputTruncated", False)
    assert result.invocation_id == payload.get("invocationId")


def test_larger_client_timeout_is_respected(sdk):
    client, call, calls, outcomes = sdk
    client.timeout = 200
    for method, args, payload in [
        (
            "list_tools",
            ["s"],
            {"tools": [], "nativeSupported": False, "truncated": False},
        ),
        ("invoke", ["s", {"tool_ref": "t"}], RESULT),
        ("start", ["s", {"tool_ref": "t"}], HANDLE),
        ("get_result", ["s", ID], HANDLE),
        ("cancel", ["s", ID], HANDLE),
    ]:
        respond(outcomes, payload)
        call(getattr(client.sessions.webmcp, method), *args)
        assert calls[-1].extensions["timeout"]["read"] == 200


@pytest.mark.parametrize(
    "method,params",
    [
        ("invoke", {"tool_ref": "t", "timeout_seconds": 121}),
        ("invoke", {"tool_ref": "t", "timeout_seconds": 0}),
        ("invoke", {"tool_ref": "t", "timeout_seconds": 1.5}),
        ("invoke", {"tool_ref": "t", "input": []}),
        ("invoke", {"tool_ref": ""}),
        ("start", {"tool_ref": "t", "timeout_seconds": 3601}),
        ("get_result", {"wait_seconds": 31}),
        ("get_result", {"wait_seconds": -1}),
    ],
)
def test_invalid_requests_fail_before_http(sdk, method, params):
    client, call, calls, outcomes = sdk
    args = ["s", ID, params] if method == "get_result" else ["s", params]
    with pytest.raises(ValidationError):
        call(getattr(client.sessions.webmcp, method), *args)
    assert not calls


@pytest.mark.parametrize("status", ["error", "outcome_unknown"])
def test_terminal_handles_without_result(sdk, status):
    client, call, calls, outcomes = sdk
    error = {"code": "outcome_unknown", "message": "Connection lost"}
    respond(outcomes, {**HANDLE, "status": status, "error": error})
    handle = call(client.sessions.webmcp.get_result, "s", ID)
    assert handle.status == status
    assert handle.result is None
    assert handle.error.code == "outcome_unknown"
