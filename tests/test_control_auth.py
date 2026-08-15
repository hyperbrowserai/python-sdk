import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from hyperbrowser import Hyperbrowser
from hyperbrowser.config import ClientConfig
from hyperbrowser.control_auth import (
    DEFAULT_BASE_URL,
    DEFAULT_FRONTEND_BASE_URL,
    resolve_control_plane_config,
    resolve_frontend_base_url,
)
from hyperbrowser.exceptions import HyperbrowserError


AUTH_ENV = (
    "HYPERBROWSER_API_KEY",
    "HYPERBROWSER_BASE_URL",
    "HYPERBROWSER_PROFILE",
    "HYPERBROWSER_FRONTEND_URL",
    "HYPERBROWSER_AUTH_LOCK_TIMEOUT_MS",
    "HYPERBROWSER_AUTH_LOCK_POLL_INTERVAL_MS",
    "HYPERBROWSER_AUTH_LOCK_STALE_MS",
)


@pytest.fixture
def auth_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    for key in AUTH_ENV:
        monkeypatch.delenv(key, raising=False)
    return tmp_path


def _expiry(*, hours=0, minutes=0):
    return (
        datetime.now(timezone.utc) + timedelta(hours=hours, minutes=minutes)
    ).isoformat()


def write_session(home, profile="default", **overrides):
    path = Path(home) / ".hx_config" / "auth" / f"{profile}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    session = {
        "version": 1,
        "base_url": DEFAULT_BASE_URL,
        "client_id": "hyperbrowser-cli",
        "token_type": "Bearer",
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expiry": _expiry(hours=1),
        "scope": "cli",
    }
    session.update(overrides)
    path.write_text(json.dumps(session) + "\n")
    return path


def _patch_httpx_client(monkeypatch, handler):
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)
    monkeypatch.setattr("hyperbrowser.control_auth.httpx.Client", fake_client)
    monkeypatch.setattr("hyperbrowser.transport.sync.httpx.Client", fake_client)


def test_missing_auth_raises(auth_home):
    with pytest.raises(HyperbrowserError, match="hx auth login") as exc:
        Hyperbrowser()
    assert exc.value.code == "missing_auth"


def test_from_env_does_not_require_api_key(auth_home):
    config = ClientConfig.from_env()
    assert config.api_key is None
    assert config.profile is None


def test_api_key_is_preferred_over_saved_session(auth_home):
    write_session(auth_home)
    base_url, auth = resolve_control_plane_config(ClientConfig(api_key="hb_live_key"))
    assert base_url == DEFAULT_BASE_URL
    assert auth.is_oauth is False
    headers, token = auth.authorize_headers()
    assert headers == {"x-api-key": "hb_live_key"}
    assert token is None


def test_env_api_key_is_preferred_over_saved_session(auth_home, monkeypatch):
    write_session(auth_home)
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")
    _, auth = resolve_control_plane_config(ClientConfig())
    headers, _ = auth.authorize_headers()
    assert headers == {"x-api-key": "env-key"}


def test_oauth_session_is_used_when_no_api_key(auth_home):
    write_session(auth_home, access_token="session-access")
    client = Hyperbrowser()
    try:
        assert client.auth.is_oauth is True
        headers, token = client.auth.authorize_headers()
        assert headers == {"authorization": "Bearer session-access"}
        assert token == "session-access"
    finally:
        client.close()


def test_profile_comes_from_constructor(auth_home):
    write_session(auth_home, profile="work", access_token="work-access")
    client = Hyperbrowser(profile="work")
    try:
        headers, _ = client.auth.authorize_headers()
        assert headers["authorization"] == "Bearer work-access"
    finally:
        client.close()


def test_profile_comes_from_env(auth_home, monkeypatch):
    write_session(auth_home, profile="ci", access_token="ci-access")
    monkeypatch.setenv("HYPERBROWSER_PROFILE", "ci")
    _, auth = resolve_control_plane_config(ClientConfig())
    headers, _ = auth.authorize_headers()
    assert headers["authorization"] == "Bearer ci-access"


def test_invalid_profile_name_is_rejected(auth_home):
    with pytest.raises(HyperbrowserError) as exc:
        Hyperbrowser(profile="bad profile")
    assert exc.value.code == "invalid_profile"


def test_base_url_strips_api_suffix(auth_home):
    write_session(auth_home)
    base_url, _ = resolve_control_plane_config(
        ClientConfig(base_url="https://api.hyperbrowser.ai/api")
    )
    assert base_url == DEFAULT_BASE_URL


def test_legacy_app_base_url_maps_to_api(auth_home):
    write_session(auth_home, base_url="https://app.hyperbrowser.ai")
    base_url, auth = resolve_control_plane_config(ClientConfig())
    assert base_url == DEFAULT_BASE_URL
    assert auth.is_oauth is True


def test_oauth_base_url_mismatch(auth_home):
    write_session(auth_home, base_url="https://staging.hyperbrowser.dev")
    with pytest.raises(HyperbrowserError) as exc:
        resolve_control_plane_config(ClientConfig())
    assert exc.value.code == "oauth_base_url_mismatch"


def test_invalid_session_json(auth_home):
    path = Path(auth_home) / ".hx_config" / "auth" / "default.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json")
    with pytest.raises(HyperbrowserError) as exc:
        resolve_control_plane_config(ClientConfig())
    assert exc.value.code == "oauth_session_invalid"


def test_resolve_frontend_base_url_defaults_and_overrides(auth_home, monkeypatch):
    assert resolve_frontend_base_url(DEFAULT_BASE_URL) == DEFAULT_FRONTEND_BASE_URL
    assert (
        resolve_frontend_base_url("https://app.hyperbrowser.ai")
        == DEFAULT_FRONTEND_BASE_URL
    )
    assert (
        resolve_frontend_base_url("https://staging.example.com")
        == "https://staging.example.com"
    )
    monkeypatch.setenv("HYPERBROWSER_FRONTEND_URL", "https://front.example.com/api")
    assert resolve_frontend_base_url(DEFAULT_BASE_URL) == "https://front.example.com"
    assert (
        resolve_frontend_base_url(
            DEFAULT_BASE_URL, explicit_frontend_url="https://explicit.example"
        )
        == "https://explicit.example"
    )


def test_refresh_uses_frontend_url_and_persists_session(auth_home, monkeypatch):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url) == f"{DEFAULT_FRONTEND_BASE_URL}/oauth/token"
        assert request.content.decode("utf-8").find("grant_type=refresh_token") >= 0
        return httpx.Response(
            200,
            json={
                "access_token": "refreshed-access",
                "refresh_token": "rotated-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "cli",
            },
        )

    _patch_httpx_client(monkeypatch, handler)
    _, auth = resolve_control_plane_config(ClientConfig())
    headers, token = auth.authorize_headers()

    assert headers == {"authorization": "Bearer refreshed-access"}
    assert token == "refreshed-access"
    assert len(requests) == 1

    saved = json.loads(
        (Path(auth_home) / ".hx_config" / "auth" / "default.json").read_text()
    )
    assert saved["access_token"] == "refreshed-access"
    assert saved["refresh_token"] == "rotated-refresh"
    assert saved["base_url"] == DEFAULT_BASE_URL


def test_async_refresh_uses_frontend_url(auth_home, monkeypatch):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "app.hyperbrowser.ai"
        return httpx.Response(
            200,
            json={"access_token": "async-refreshed", "expires_in": 3600},
        )

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("hyperbrowser.control_auth.httpx.AsyncClient", fake_client)
    _, auth = resolve_control_plane_config(ClientConfig())
    headers, token = asyncio.run(auth.aauthorize_headers())
    assert headers == {"authorization": "Bearer async-refreshed"}
    assert token == "async-refreshed"


def test_expired_refresh_token_deletes_session(auth_home):
    path = write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
        refresh_token_expiry=_expiry(minutes=-1),
    )
    _, auth = resolve_control_plane_config(ClientConfig())
    with pytest.raises(HyperbrowserError) as exc:
        auth.authorize_headers()
    assert exc.value.code == "oauth_session_expired"
    assert path.exists() is False


def test_invalid_grant_deletes_session(auth_home, monkeypatch):
    path = write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    _patch_httpx_client(monkeypatch, handler)
    _, auth = resolve_control_plane_config(ClientConfig())
    with pytest.raises(HyperbrowserError) as exc:
        auth.authorize_headers()
    assert exc.value.code == "invalid_grant"
    assert path.exists() is False


def test_rotation_lock_timeout(auth_home):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )
    session_path = Path(auth_home) / ".hx_config" / "auth" / "default.json"
    lock_path = Path(f"{session_path}.refresh.lock")
    lock_path.write_text("pid=1\ncreated_at=2020-01-01T00:00:00Z\n")

    _, auth = resolve_control_plane_config(
        ClientConfig(auth_lock_timeout_ms=40, auth_lock_poll_interval_ms=10)
    )
    with pytest.raises(HyperbrowserError) as exc:
        auth.authorize_headers()
    assert exc.value.code == "auth_rotation_timeout"


def test_stale_rotation_lock_is_cleared(auth_home, monkeypatch):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )
    session_path = Path(auth_home) / ".hx_config" / "auth" / "default.json"
    lock_path = Path(f"{session_path}.refresh.lock")
    lock_path.write_text("pid=1\n")
    import os

    os.utime(lock_path, (0, 0))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"access_token": "after-stale-lock", "expires_in": 3600},
        )

    _patch_httpx_client(monkeypatch, handler)
    _, auth = resolve_control_plane_config(
        ClientConfig(auth_lock_stale_ms=1, auth_lock_timeout_ms=200)
    )
    headers, _ = auth.authorize_headers()
    assert headers["authorization"] == "Bearer after-stale-lock"
    assert lock_path.exists() is False
