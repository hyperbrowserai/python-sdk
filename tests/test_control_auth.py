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
    DEFAULT_OAUTH_REFRESH_TIMEOUT_S,
    _parse_timestamp,
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


def test_from_env_requires_api_key(auth_home):
    with pytest.raises(
        ValueError, match="HYPERBROWSER_API_KEY environment variable is required"
    ):
        ClientConfig.from_env()


def test_from_env_reads_api_key(auth_home, monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")
    config = ClientConfig.from_env()
    assert config.api_key == "env-key"


def test_client_config_positional_runtime_proxy_override_is_preserved():
    config = ClientConfig("key", "https://api.example", "socks5://proxy")
    assert config.api_key == "key"
    assert config.base_url == "https://api.example"
    assert config.runtime_proxy_override == "socks5://proxy"
    assert config.profile is None


def test_api_key_is_preferred_over_saved_session(auth_home):
    write_session(auth_home)
    base_url, auth = resolve_control_plane_config(ClientConfig(api_key="hb_live_key"))
    assert base_url == DEFAULT_BASE_URL
    assert auth.is_oauth is False
    headers, token = auth.authorize_headers()
    assert headers == {"x-api-key": "hb_live_key"}
    assert token is None


def test_constructor_env_api_key_is_preferred_over_saved_session(
    auth_home, monkeypatch
):
    write_session(auth_home)
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")
    client = Hyperbrowser()
    try:
        headers, _ = client.auth.authorize_headers()
    finally:
        client.close()
    assert headers == {"x-api-key": "env-key"}


def test_explicit_empty_api_key_raises(auth_home, monkeypatch):
    write_session(auth_home)
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")
    with pytest.raises(HyperbrowserError, match="API key must be provided") as exc:
        Hyperbrowser(api_key="")
    assert exc.value.code == "missing_auth"


def test_client_config_none_api_key_does_not_read_env_key(auth_home, monkeypatch):
    write_session(auth_home, access_token="session-access")
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")
    _, auth = resolve_control_plane_config(ClientConfig(api_key=None))
    headers, _ = auth.authorize_headers()
    assert headers == {"authorization": "Bearer session-access"}


def test_passed_config_ignores_env_base_url(auth_home, monkeypatch):
    write_session(auth_home)
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://staging.hyperbrowser.dev")
    client = Hyperbrowser(config=ClientConfig())
    try:
        assert client.config.base_url == DEFAULT_BASE_URL
        assert client.auth.is_oauth is True
    finally:
        client.close()


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
    client = Hyperbrowser()
    try:
        headers, _ = client.auth.authorize_headers()
    finally:
        client.close()
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


def test_default_client_adopts_session_base_url(auth_home):
    write_session(auth_home, base_url="https://staging.hyperbrowser.dev")
    base_url, auth = resolve_control_plane_config(ClientConfig())
    assert base_url == "https://staging.hyperbrowser.dev"
    assert auth.is_oauth is True


def test_oauth_base_url_mismatch(auth_home):
    write_session(auth_home, base_url="https://staging.hyperbrowser.dev")
    with pytest.raises(HyperbrowserError) as exc:
        resolve_control_plane_config(
            ClientConfig(base_url="https://other.hyperbrowser.dev")
        )
    assert exc.value.code == "oauth_base_url_mismatch"


def test_empty_base_url_raises(auth_home):
    write_session(auth_home)
    with pytest.raises(HyperbrowserError) as exc:
        resolve_control_plane_config(ClientConfig(api_key="key", base_url=""))
    assert exc.value.code == "invalid_base_url"


def test_empty_env_api_key_falls_back_to_oauth(auth_home, monkeypatch):
    write_session(auth_home, access_token="session-access")
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "   ")
    client = Hyperbrowser()
    try:
        headers, _ = client.auth.authorize_headers()
    finally:
        client.close()
    assert headers == {"authorization": "Bearer session-access"}


def test_api_key_mode_does_not_rewrite_explicit_base_url(auth_home):
    base_url, auth = resolve_control_plane_config(
        ClientConfig(api_key="key", base_url="https://app.hyperbrowser.ai/api")
    )
    assert base_url == "https://app.hyperbrowser.ai/api"
    assert auth.is_oauth is False


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
    assert (
        resolve_frontend_base_url(
            DEFAULT_BASE_URL, explicit_frontend_url="https://explicit.example"
        )
        == "https://explicit.example"
    )
    monkeypatch.setenv("HYPERBROWSER_FRONTEND_URL", "https://front.example.com/api")
    assert resolve_frontend_base_url(DEFAULT_BASE_URL) == DEFAULT_FRONTEND_BASE_URL


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

    _patch_httpx_client(monkeypatch, handler)
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


def test_stale_lock_clear_does_not_delete_replaced_lock(auth_home, monkeypatch):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )
    session_path = Path(auth_home) / ".hx_config" / "auth" / "default.json"
    lock_path = Path(f"{session_path}.refresh.lock")
    lock_path.write_text("pid=old\n")
    import os

    os.utime(lock_path, (0, 0))

    original_clear = None
    from hyperbrowser.control_auth import ControlPlaneAuthManager

    original_clear = ControlPlaneAuthManager._clear_stale_rotation_lock

    def wrap(self):
        original_clear(self)
        lock_path.write_text("pid=fresh\n")

    monkeypatch.setattr(ControlPlaneAuthManager, "_clear_stale_rotation_lock", wrap)

    _, auth = resolve_control_plane_config(
        ClientConfig(auth_lock_stale_ms=1, auth_lock_timeout_ms=40)
    )
    with pytest.raises(HyperbrowserError) as exc:
        auth.authorize_headers()
    assert exc.value.code == "auth_rotation_timeout"
    assert lock_path.read_text() == "pid=fresh\n"


def test_refresh_without_expires_in_does_not_keep_old_expiry(auth_home, monkeypatch):
    old_expiry = _expiry(minutes=-5)
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=old_expiry,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "no-expiry-access",
                "refresh_token": "same-refresh",
            },
        )

    _patch_httpx_client(monkeypatch, handler)
    _, auth = resolve_control_plane_config(ClientConfig())
    headers, token = auth.authorize_headers()
    assert headers == {"authorization": "Bearer no-expiry-access"}
    assert token == "no-expiry-access"

    saved = json.loads(
        (Path(auth_home) / ".hx_config" / "auth" / "default.json").read_text()
    )
    assert saved["access_token"] == "no-expiry-access"
    assert saved["expiry"] == ""
    headers_again, _ = auth.authorize_headers()
    assert headers_again == {"authorization": "Bearer no-expiry-access"}


def test_parse_timestamp_accepts_variable_fractional_seconds():
    assert _parse_timestamp("2026-08-15T12:00:00Z") is not None
    assert _parse_timestamp("2026-08-15T12:00:00.1Z") is not None
    assert _parse_timestamp("2026-08-15T12:00:00.123456789+00:00") is not None
    assert _parse_timestamp("2026-08-15T12:00:00.123456789Z") is not None
    nine = _parse_timestamp("2026-08-15T12:00:00.123456789Z")
    six = _parse_timestamp("2026-08-15T12:00:00.123456Z")
    assert nine is not None and six is not None
    assert abs(nine - six) < 0.001


def test_invalid_grant_does_not_delete_rotated_session(auth_home, monkeypatch):
    path = write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
        refresh_token="old-refresh",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "base_url": DEFAULT_BASE_URL,
                    "client_id": "hyperbrowser-cli",
                    "token_type": "Bearer",
                    "access_token": "rotated-access",
                    "refresh_token": "rotated-refresh",
                    "expiry": _expiry(hours=1),
                    "scope": "cli",
                }
            )
        )
        return httpx.Response(400, json={"error": "invalid_grant"})

    _patch_httpx_client(monkeypatch, handler)
    _, auth = resolve_control_plane_config(ClientConfig())
    with pytest.raises(HyperbrowserError) as exc:
        auth.authorize_headers()
    assert exc.value.code == "invalid_grant"
    saved = json.loads(path.read_text())
    assert saved["refresh_token"] == "rotated-refresh"
    assert saved["access_token"] == "rotated-access"


def test_missing_session_after_expire_is_oauth_session_expired(auth_home):
    path = write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
        refresh_token_expiry=_expiry(minutes=-1),
    )
    _, auth = resolve_control_plane_config(ClientConfig())
    path.unlink()
    with pytest.raises(HyperbrowserError) as exc:
        auth.authorize_headers()
    assert exc.value.code == "oauth_session_expired"


def test_sync_transport_accepts_api_key_string():
    from hyperbrowser.transport.sync import SyncTransport

    transport = SyncTransport("legacy-key")
    try:
        headers, token = transport.auth.authorize_headers()
        assert headers == {"x-api-key": "legacy-key"}
        assert token is None
        assert transport.auth.is_oauth is False
    finally:
        transport.close()


def test_refresh_timeout_is_independent_of_lock_timeout(auth_home, monkeypatch):
    write_session(
        auth_home,
        access_token="expired-access",
        expiry=_expiry(minutes=-5),
    )
    seen = []

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        seen.append(kwargs.get("timeout"))
        kwargs["transport"] = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 3600},
            )
        )
        return real_client(*args, **kwargs)

    monkeypatch.setattr("hyperbrowser.control_auth.httpx.Client", fake_client)
    _, auth = resolve_control_plane_config(ClientConfig(auth_lock_timeout_ms=5))
    auth.authorize_headers()
    assert seen
    assert seen[0] == DEFAULT_OAUTH_REFRESH_TIMEOUT_S
