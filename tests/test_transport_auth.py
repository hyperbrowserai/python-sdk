import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError

from tests.test_control_auth import (
    AUTH_ENV,
    _patch_httpx_client,
    write_session,
)
from tests.test_sandbox_wire_contract import SANDBOX_DETAIL_PAYLOAD


@pytest.fixture
def auth_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    for key in AUTH_ENV:
        monkeypatch.delenv(key, raising=False)
    return tmp_path


def test_api_key_requests_send_x_api_key(auth_home, monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers.get("x-api-key") == "test-api-key"
        return httpx.Response(200, json={"jobId": "job_123"})

    _patch_httpx_client(monkeypatch, handler)
    client = Hyperbrowser(api_key="test-api-key", base_url="https://api.example")
    try:
        started = client.scrape.start({"url": "https://example.com"})
    finally:
        client.close()

    assert started.job_id == "job_123"
    assert len(seen) == 1


def test_oauth_401_refreshes_and_retries(auth_home, monkeypatch):
    write_session(auth_home, access_token="old-access")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            (request.method, request.url.path, request.headers.get("authorization"))
        )
        if request.url.path == "/oauth/token":
            assert request.url.host == "app.hyperbrowser.ai"
            return httpx.Response(
                200,
                json={"access_token": "new-access", "expires_in": 3600},
            )
        if request.url.path == "/api/scrape":
            if request.headers.get("authorization") == "Bearer old-access":
                return httpx.Response(401, json={"message": "unauthorized"})
            assert request.headers.get("authorization") == "Bearer new-access"
            return httpx.Response(200, json={"jobId": "job_456"})
        return httpx.Response(404, json={"message": "not found"})

    _patch_httpx_client(monkeypatch, handler)
    client = Hyperbrowser()
    try:
        started = client.scrape.start({"url": "https://example.com"})
    finally:
        client.close()

    assert started.job_id == "job_456"
    assert calls == [
        ("POST", "/api/scrape", "Bearer old-access"),
        ("POST", "/oauth/token", None),
        ("POST", "/api/scrape", "Bearer new-access"),
    ]


def test_oauth_401_without_replayable_body_does_not_retry(
    auth_home, monkeypatch, tmp_path
):
    write_session(auth_home, access_token="old-access")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            raise AssertionError("refresh should not run for non-replayable uploads")
        return httpx.Response(401, json={"message": "unauthorized"})

    _patch_httpx_client(monkeypatch, handler)
    upload = tmp_path / "file.bin"
    upload.write_bytes(b"hello")
    client = Hyperbrowser()
    try:
        with pytest.raises(HyperbrowserError) as exc:
            client.sessions.upload_file("session_123", str(upload))
        assert exc.value.status_code == 401
    finally:
        client.close()


def test_post_timeout_is_forwarded(auth_home, monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions.get("timeout"))
        return httpx.Response(
            200,
            json={
                "success": True,
                "iterationsRequested": 1,
                "iterationsRun": 1,
                "solved": False,
                "solvedCaptchas": [],
                "pages": [],
            },
        )

    _patch_httpx_client(monkeypatch, handler)
    client = Hyperbrowser(api_key="test-api-key", timeout=12)
    try:
        client.sessions.evaluate_captcha("session_123")
    finally:
        client.close()

    assert seen
    timeout = seen[0]
    assert timeout is not None
    if isinstance(timeout, dict):
        timeout_values = list(timeout.values())
    else:
        timeout_values = [
            getattr(timeout, name, None)
            for name in ("read", "write", "connect", "pool")
        ]
    assert any(value is not None and value >= 12 for value in timeout_values)


def test_async_api_key_and_oauth_retry(auth_home, monkeypatch):
    write_session(auth_home, access_token="old-access")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            (request.method, request.url.path, request.headers.get("authorization"))
        )
        if request.url.path == "/oauth/token":
            return httpx.Response(
                200,
                json={"access_token": "new-access", "expires_in": 3600},
            )
        if request.headers.get("authorization") == "Bearer old-access":
            return httpx.Response(401, json={"message": "unauthorized"})
        return httpx.Response(200, json={"jobId": "job_async"})

    real_async = httpx.AsyncClient

    def fake_async(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async(*args, **kwargs)

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        "hyperbrowser.transport.async_transport.httpx.AsyncClient", fake_async
    )
    monkeypatch.setattr("hyperbrowser.control_auth.httpx.AsyncClient", fake_async)
    monkeypatch.setattr("hyperbrowser.control_auth.httpx.Client", fake_client)

    async def run():
        client = AsyncHyperbrowser()
        try:
            return await client.scrape.start({"url": "https://example.com"})
        finally:
            await client.close()

    started = asyncio.run(run())
    assert started.job_id == "job_async"
    assert ("POST", "/oauth/token", None) in calls


def test_client_config_frontend_url_is_used_for_refresh(auth_home, monkeypatch):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=(datetime.now(timezone.utc) + timedelta(minutes=-5)).isoformat(),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://front.example/oauth/token"
        return httpx.Response(
            200,
            json={"access_token": "front-access", "expires_in": 3600},
        )

    _patch_httpx_client(monkeypatch, handler)
    client = Hyperbrowser(config=ClientConfig(frontend_url="https://front.example"))
    try:
        headers, _ = client.auth.authorize_headers()
    finally:
        client.close()
    assert headers["authorization"] == "Bearer front-access"


def test_sandbox_control_requests_include_api_key(auth_home, monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            {
                "path": request.url.path,
                "api_key": request.headers.get("x-api-key"),
            }
        )
        return httpx.Response(200, json=SANDBOX_DETAIL_PAYLOAD)

    _patch_httpx_client(monkeypatch, handler)
    client = Hyperbrowser(api_key="sandbox-key", base_url="https://api.example")
    try:
        client.sandboxes.get_detail("sbx_123")
    finally:
        client.close()

    assert seen
    assert seen[0]["path"] == "/api/sandbox/sbx_123"
    assert seen[0]["api_key"] == "sandbox-key"
