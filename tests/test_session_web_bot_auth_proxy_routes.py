import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSessionParams,
    ProxyRoute,
    SessionLaunchState,
    WebBotAuthParams,
)


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def sdk(request):
    """Exercise the same wire contract through both public clients and transports."""
    is_async = request.param
    loop = asyncio.new_event_loop()
    client = (AsyncHyperbrowser if is_async else Hyperbrowser)(api_key="test-key")
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(400, json={"message": "fixture stops before parsing"})

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
    yield client, call, calls
    call(client.close)
    loop.close()


def sent_bodies(sdk, method, params_list):
    client, call, calls = sdk
    for params in params_list:
        with pytest.raises(HyperbrowserError):
            call(method, params)
    return [json.loads(req.content) for req in calls]


def test_web_bot_auth_on_the_wire(sdk):
    client = sdk[0]
    bodies = sent_bodies(
        sdk,
        client.sessions.create,
        [
            {},
            {"web_bot_auth": True},
            {"web_bot_auth": False},
            {"web_bot_auth": {"only_domains": ["example.com", "shop.example.org"]}},
            CreateSessionParams(web_bot_auth=True),
            CreateSessionParams(
                web_bot_auth=WebBotAuthParams(only_domains=["example.com"])
            ),
        ],
    )
    assert "webBotAuth" not in bodies[0]
    assert bodies[1]["webBotAuth"] is True
    assert bodies[2]["webBotAuth"] is False
    assert bodies[3]["webBotAuth"] == {
        "onlyDomains": ["example.com", "shop.example.org"]
    }
    assert bodies[4]["webBotAuth"] is True
    assert bodies[5]["webBotAuth"] == {"onlyDomains": ["example.com"]}


def test_proxy_routes_on_the_wire_in_order(sdk):
    client = sdk[0]
    routes = [
        {"match": "api.example.com", "proxy": "default"},
        {"match": ["*.example.com", "cdn.example.net"], "proxy": "direct"},
    ]
    bodies = sent_bodies(
        sdk,
        client.sessions.create,
        [
            {"use_proxy": True, "proxy_routes": routes},
            CreateSessionParams(
                use_proxy=True,
                proxy_routes=[ProxyRoute(**route) for route in routes],
            ),
        ],
    )
    for body in bodies:
        assert body["useProxy"] is True
        assert body["proxyRoutes"] == routes


def test_agent_tasks_pass_web_bot_auth_through_session_options(sdk):
    client = sdk[0]
    bodies = sent_bodies(
        sdk,
        client.agents.browser_use.start,
        [
            {
                "task": "Open example.com",
                "session_options": {"web_bot_auth": {"only_domains": ["example.com"]}},
            }
        ],
    )
    assert sdk[2][0].url.path == "/api/task/browser-use"
    assert bodies[0]["sessionOptions"]["webBotAuth"] == {"onlyDomains": ["example.com"]}


def test_misspelled_or_invalid_options_fail_before_sending(sdk):
    client, call, calls = sdk
    for params in [
        # A dropped key would sign requests to every host instead of example.com.
        {"web_bot_auth": {"onlyDomains": ["example.com"]}},
        {"proxy_routes": [{"match": "example.com", "proxy": "upstream"}]},
        {"proxy_routes": [{"match": "example.com"}]},
        {"proxy_routes": [{"match": "example.com", "proxy": "direct", "port": 443}]},
    ]:
        with pytest.raises(ValidationError):
            call(client.sessions.create, params)
    assert calls == []


def test_launch_state_reports_how_a_session_signs():
    state = SessionLaunchState.model_validate(
        {
            "webBotAuth": {
                "signatureAgent": "https://www.hyperbrowser.ai",
                "onlyDomains": ["example.com"],
            }
        }
    )
    assert state.web_bot_auth is not None
    assert state.web_bot_auth.signature_agent == "https://www.hyperbrowser.ai"
    assert state.web_bot_auth.only_domains == ["example.com"]
    unscoped = SessionLaunchState.model_validate(
        {"webBotAuth": {"signatureAgent": "https://www.hyperbrowser.ai"}}
    )
    assert unscoped.web_bot_auth is not None
    assert unscoped.web_bot_auth.only_domains is None
    assert SessionLaunchState().web_bot_auth is None
