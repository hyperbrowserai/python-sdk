import asyncio
import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from .config import ClientConfig
from .exceptions import HyperbrowserError

DEFAULT_PROFILE = "default"
DEFAULT_BASE_URL = "https://api.hyperbrowser.ai"
DEFAULT_LOCK_TIMEOUT_MS = 30000
DEFAULT_LOCK_POLL_INTERVAL_MS = 125
DEFAULT_LOCK_STALE_MS = 120000
OAUTH_REFRESH_EARLY_EXPIRY_MS = 30000
PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

ENV_PROFILE = "HYPERBROWSER_PROFILE"
ENV_API_KEY = "HYPERBROWSER_API_KEY"
ENV_BASE_URL = "HYPERBROWSER_BASE_URL"
ENV_LOCK_TIMEOUT_MS = "HYPERBROWSER_AUTH_LOCK_TIMEOUT_MS"
ENV_LOCK_POLL_INTERVAL_MS = "HYPERBROWSER_AUTH_LOCK_POLL_INTERVAL_MS"
ENV_LOCK_STALE_MS = "HYPERBROWSER_AUTH_LOCK_STALE_MS"


class ControlPlaneAuthManager:
    def __init__(self, mode: Dict[str, object]):
        self._mode = mode

    @property
    def is_oauth(self) -> bool:
        return self._mode["kind"] == "oauth"

    def authorize_headers(
        self,
        *,
        force_refresh: bool = False,
        rejected_access_token: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Optional[str]]:
        if self._mode["kind"] == "api_key":
            return {"x-api-key": str(self._mode["api_key"])}, None

        access_token = self._resolve_oauth_access_token(
            force_refresh=force_refresh,
            rejected_access_token=rejected_access_token,
        )
        return {"authorization": f"Bearer {access_token}"}, access_token

    async def aauthorize_headers(
        self,
        *,
        force_refresh: bool = False,
        rejected_access_token: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Optional[str]]:
        if self._mode["kind"] == "api_key":
            return {"x-api-key": str(self._mode["api_key"])}, None

        access_token = await self._aresolve_oauth_access_token(
            force_refresh=force_refresh,
            rejected_access_token=rejected_access_token,
        )
        return {"authorization": f"Bearer {access_token}"}, access_token

    def _resolve_oauth_access_token(
        self,
        *,
        force_refresh: bool,
        rejected_access_token: Optional[str],
    ) -> str:
        session, session_mtime_ns = self._load_oauth_session_with_mtime()
        if _should_use_oauth_session(session, force_refresh, rejected_access_token):
            return _normalize_text(session["access_token"])

        deadline = time.monotonic() + (int(self._mode["lock_timeout_ms"]) / 1000.0)
        while True:
            lock_fd = self._try_acquire_rotation_lock()
            if lock_fd is not None:
                try:
                    session, session_mtime_ns = self._load_oauth_session_with_mtime()
                    if _should_use_oauth_session(
                        session, force_refresh, rejected_access_token
                    ):
                        return _normalize_text(session["access_token"])
                    if _is_refresh_token_expired(session):
                        raise HyperbrowserError(
                            "OAuth session refresh token expired",
                            code="oauth_session_expired",
                            retryable=False,
                            service="control",
                        )
                    refreshed = self._refresh_oauth_session(session)
                    return _normalize_text(refreshed["access_token"])
                finally:
                    self._release_rotation_lock(lock_fd)

            self._clear_stale_rotation_lock()
            if time.monotonic() > deadline:
                raise HyperbrowserError(
                    "Timed out waiting for OAuth rotation lock",
                    code="auth_rotation_timeout",
                    retryable=False,
                    service="control",
                )

            time.sleep(int(self._mode["lock_poll_interval_ms"]) / 1000.0)
            updated = self._load_updated_oauth_session(session_mtime_ns)
            if updated is None:
                continue
            session, session_mtime_ns = updated
            if _should_use_oauth_session(session, True, rejected_access_token):
                return _normalize_text(session["access_token"])
            if _is_refresh_token_expired(session):
                raise HyperbrowserError(
                    "OAuth session refresh token expired",
                    code="oauth_session_expired",
                    retryable=False,
                    service="control",
                )

    async def _aresolve_oauth_access_token(
        self,
        *,
        force_refresh: bool,
        rejected_access_token: Optional[str],
    ) -> str:
        session, session_mtime_ns = self._load_oauth_session_with_mtime()
        if _should_use_oauth_session(session, force_refresh, rejected_access_token):
            return _normalize_text(session["access_token"])

        deadline = time.monotonic() + (int(self._mode["lock_timeout_ms"]) / 1000.0)
        while True:
            lock_fd = self._try_acquire_rotation_lock()
            if lock_fd is not None:
                try:
                    session, session_mtime_ns = self._load_oauth_session_with_mtime()
                    if _should_use_oauth_session(
                        session, force_refresh, rejected_access_token
                    ):
                        return _normalize_text(session["access_token"])
                    if _is_refresh_token_expired(session):
                        raise HyperbrowserError(
                            "OAuth session refresh token expired",
                            code="oauth_session_expired",
                            retryable=False,
                            service="control",
                        )
                    refreshed = await self._arefresh_oauth_session(session)
                    return _normalize_text(refreshed["access_token"])
                finally:
                    self._release_rotation_lock(lock_fd)

            self._clear_stale_rotation_lock()
            if time.monotonic() > deadline:
                raise HyperbrowserError(
                    "Timed out waiting for OAuth rotation lock",
                    code="auth_rotation_timeout",
                    retryable=False,
                    service="control",
                )

            await asyncio.sleep(int(self._mode["lock_poll_interval_ms"]) / 1000.0)
            updated = self._load_updated_oauth_session(session_mtime_ns)
            if updated is None:
                continue
            session, session_mtime_ns = updated
            if _should_use_oauth_session(session, True, rejected_access_token):
                return _normalize_text(session["access_token"])
            if _is_refresh_token_expired(session):
                raise HyperbrowserError(
                    "OAuth session refresh token expired",
                    code="oauth_session_expired",
                    retryable=False,
                    service="control",
                )

    def _load_oauth_session(self) -> Dict[str, str]:
        session_path = Path(str(self._mode["session_path"]))
        try:
            raw = session_path.read_text()
        except (FileNotFoundError, OSError) as error:
            raise HyperbrowserError(
                "Failed to read saved OAuth session",
                code="oauth_session_read_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

        try:
            session = json.loads(raw)
        except json.JSONDecodeError as error:
            raise HyperbrowserError(
                "Saved OAuth session is invalid JSON",
                code="oauth_session_invalid",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

        _validate_oauth_session(session, expected_base_url=str(self._mode["base_url"]))
        return session

    def _load_oauth_session_with_mtime(self) -> Tuple[Dict[str, str], Optional[int]]:
        session = self._load_oauth_session()
        return session, self._get_session_mtime_ns()

    def _load_updated_oauth_session(
        self, previous_mtime_ns: Optional[int]
    ) -> Optional[Tuple[Dict[str, str], Optional[int]]]:
        current_mtime_ns = self._get_session_mtime_ns()
        if current_mtime_ns == previous_mtime_ns:
            return None
        return self._load_oauth_session(), current_mtime_ns

    def _get_session_mtime_ns(self) -> Optional[int]:
        session_path = Path(str(self._mode["session_path"]))
        try:
            return session_path.stat().st_mtime_ns
        except (FileNotFoundError, OSError) as error:
            raise HyperbrowserError(
                "Failed to inspect saved OAuth session",
                code="oauth_session_read_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

    def _refresh_oauth_session(self, session: Dict[str, str]) -> Dict[str, str]:
        try:
            with httpx.Client(
                timeout=int(self._mode["lock_timeout_ms"]) / 1000.0
            ) as client:
                response = client.post(
                    f"{self._mode['base_url']}/oauth/token",
                    headers={"content-type": "application/x-www-form-urlencoded"},
                    content=_build_refresh_form(session),
                )
        except Exception as error:
            raise HyperbrowserError(
                "Failed to refresh OAuth session",
                code="oauth_refresh_failed",
                retryable=True,
                service="control",
                cause=error,
                original_error=error if isinstance(error, Exception) else None,
            )

        return self._handle_refresh_response(session, response)

    async def _arefresh_oauth_session(self, session: Dict[str, str]) -> Dict[str, str]:
        try:
            async with httpx.AsyncClient(
                timeout=int(self._mode["lock_timeout_ms"]) / 1000.0
            ) as client:
                response = await client.post(
                    f"{self._mode['base_url']}/oauth/token",
                    headers={"content-type": "application/x-www-form-urlencoded"},
                    content=_build_refresh_form(session),
                )
        except Exception as error:
            raise HyperbrowserError(
                "Failed to refresh OAuth session",
                code="oauth_refresh_failed",
                retryable=True,
                service="control",
                cause=error,
                original_error=error if isinstance(error, Exception) else None,
            )

        return self._handle_refresh_response(session, response)

    def _handle_refresh_response(
        self, session: Dict[str, str], response: httpx.Response
    ) -> Dict[str, str]:
        raw_text = response.text
        payload: Any = {}
        if raw_text:
            try:
                payload = response.json()
            except ValueError:
                payload = {}

        if response.status_code >= 400:
            message = (
                _normalize_text(
                    _string_value(payload.get("message")) if isinstance(payload, dict) else ""
                )
                or _normalize_text(
                    _string_value(payload.get("error")) if isinstance(payload, dict) else ""
                )
                or f"OAuth refresh failed with status {response.status_code}"
            )
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                code=(
                    _normalize_text(
                        _string_value(payload.get("code")) if isinstance(payload, dict) else ""
                    )
                    or "oauth_refresh_failed"
                ),
                retryable=False,
                service="control",
                details=_redact_refresh_error_details(payload),
                response=response,
            )

        if not isinstance(payload, dict):
            payload = {}

        refreshed = _build_refreshed_oauth_session(session, payload)
        _write_oauth_session_atomic(Path(str(self._mode["session_path"])), refreshed)
        return refreshed

    def _try_acquire_rotation_lock(self) -> Optional[int]:
        lock_path = Path(str(self._mode["lock_path"]))
        lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(lock_path.parent, 0o700)
        except OSError:
            pass

        try:
            lock_fd = os.open(
                str(lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            return None
        except OSError as error:
            raise HyperbrowserError(
                "Failed to create OAuth rotation lock",
                code="auth_rotation_lock_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

        try:
            os.write(
                lock_fd,
                f"pid={os.getpid()}\ncreated_at={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n".encode(
                    "utf-8"
                ),
            )
            os.fsync(lock_fd)
            return lock_fd
        except OSError as error:
            try:
                os.close(lock_fd)
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise HyperbrowserError(
                "Failed to create OAuth rotation lock",
                code="auth_rotation_lock_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

    def _clear_stale_rotation_lock(self) -> None:
        lock_path = Path(str(self._mode["lock_path"]))
        try:
            stat = lock_path.stat()
        except FileNotFoundError:
            return
        except OSError as error:
            raise HyperbrowserError(
                "Failed to inspect OAuth rotation lock",
                code="auth_rotation_lock_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

        if (time.time() * 1000) - (stat.st_mtime * 1000) < int(
            self._mode["lock_stale_ms"]
        ):
            return

        try:
            lock_path.unlink(missing_ok=True)
        except OSError as error:
            raise HyperbrowserError(
                "Failed to remove stale OAuth rotation lock",
                code="auth_rotation_lock_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

    def _release_rotation_lock(self, lock_fd: int) -> None:
        lock_path = Path(str(self._mode["lock_path"]))
        try:
            os.close(lock_fd)
        except OSError:
            pass
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def resolve_control_plane_config(
    config: ClientConfig,
) -> Tuple[str, ControlPlaneAuthManager]:
    explicit_api_key = _normalize_text(config.api_key or "")
    env_api_key = _normalize_text(os.environ.get(ENV_API_KEY, ""))
    explicit_base_url = _normalize_base_url(config.base_url)
    env_base_url = _normalize_base_url(os.environ.get(ENV_BASE_URL, ""))

    if explicit_api_key or env_api_key:
        return (
            explicit_base_url or env_base_url or DEFAULT_BASE_URL,
            ControlPlaneAuthManager(
                {"kind": "api_key", "api_key": explicit_api_key or env_api_key}
            ),
        )

    profile = _normalize_profile(
        config.profile or os.environ.get(ENV_PROFILE) or DEFAULT_PROFILE
    )
    session_path = _resolve_oauth_session_path(profile)
    session = _try_load_oauth_session(session_path)

    resolved_base_url = (
        explicit_base_url
        or env_base_url
        or _normalize_base_url((session or {}).get("base_url", ""))
        or DEFAULT_BASE_URL
    )

    if session is None:
        raise HyperbrowserError(
            "API key must be provided or an OAuth session must be saved with hx auth login",
            code="missing_auth",
            retryable=False,
            service="control",
        )

    if _normalize_base_url(session["base_url"]) != resolved_base_url:
        raise HyperbrowserError(
            f"Saved OAuth session for profile {profile} targets {_normalize_base_url(session['base_url'])}, not {resolved_base_url}",
            code="oauth_base_url_mismatch",
            retryable=False,
            service="control",
        )

    return resolved_base_url, ControlPlaneAuthManager(
        {
            "kind": "oauth",
            "profile": profile,
            "session_path": str(session_path),
            "lock_path": f"{session_path}.refresh.lock",
            "base_url": resolved_base_url,
            "lock_timeout_ms": _normalize_positive_int(
                config.auth_lock_timeout_ms,
                os.environ.get(ENV_LOCK_TIMEOUT_MS),
                DEFAULT_LOCK_TIMEOUT_MS,
            ),
            "lock_poll_interval_ms": _normalize_positive_int(
                config.auth_lock_poll_interval_ms,
                os.environ.get(ENV_LOCK_POLL_INTERVAL_MS),
                DEFAULT_LOCK_POLL_INTERVAL_MS,
            ),
            "lock_stale_ms": _normalize_positive_int(
                config.auth_lock_stale_ms,
                os.environ.get(ENV_LOCK_STALE_MS),
                DEFAULT_LOCK_STALE_MS,
            ),
        }
    )


def _resolve_oauth_session_path(profile: str) -> Path:
    return Path.home() / ".hx_config" / "auth" / f"{profile}.json"


def _try_load_oauth_session(session_path: Path) -> Optional[Dict[str, str]]:
    try:
        raw = session_path.read_text()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise HyperbrowserError(
            "Failed to read saved OAuth session",
            code="oauth_session_read_failed",
            retryable=False,
            service="control",
            cause=error,
            original_error=error,
        )

    try:
        session = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HyperbrowserError(
            "Saved OAuth session is invalid JSON",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
            cause=error,
            original_error=error,
        )

    _validate_oauth_session(session)
    return session


def _validate_oauth_session(
    session: Dict[str, str], expected_base_url: Optional[str] = None
) -> None:
    if not isinstance(session, dict):
        raise HyperbrowserError(
            "Saved OAuth session is invalid",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )

    access_token = _normalize_text(session.get("access_token", ""))
    refresh_token = _normalize_text(session.get("refresh_token", ""))
    base_url = _normalize_base_url(session.get("base_url", ""))

    if access_token == "" or refresh_token == "":
        raise HyperbrowserError(
            "Saved OAuth session is missing tokens",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )
    if base_url == "":
        raise HyperbrowserError(
            "Saved OAuth session is missing a base URL",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )
    if _parse_timestamp(session.get("expiry")) is None:
        raise HyperbrowserError(
            "Saved OAuth session has an invalid expiry",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )

    refresh_expiry = _normalize_text(session.get("refresh_token_expiry", ""))
    if refresh_expiry and _parse_timestamp(refresh_expiry) is None:
        raise HyperbrowserError(
            "Saved OAuth session has an invalid refresh token expiry",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )

    if expected_base_url and base_url != _normalize_base_url(expected_base_url):
        raise HyperbrowserError(
            "Saved OAuth session targets a different base URL",
            code="oauth_base_url_mismatch",
            retryable=False,
            service="control",
        )


def _build_refresh_form(session: Dict[str, str]) -> str:
    return urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": _normalize_text(session.get("client_id", ""))
            or "hyperbrowser-cli",
            "refresh_token": _normalize_text(session.get("refresh_token", "")),
        }
    )


def _build_refreshed_oauth_session(
    previous: Dict[str, str], payload: Dict[str, object]
) -> Dict[str, str]:
    access_token = _normalize_text(_string_value(payload.get("access_token")))
    if access_token == "":
        raise HyperbrowserError(
            "OAuth refresh response did not include an access token",
            code="oauth_refresh_failed",
            retryable=False,
            service="control",
            details=payload,
        )

    refresh_token = _normalize_text(
        _string_value(payload.get("refresh_token"))
    ) or _normalize_text(previous.get("refresh_token", ""))
    token_type = (
        _normalize_text(_string_value(payload.get("token_type")))
        or _normalize_text(previous.get("token_type", ""))
        or "Bearer"
    )
    expiry = _derive_expiry(payload.get("expires_in")) or _normalize_text(
        previous.get("expiry", "")
    )
    refresh_expiry = _derive_expiry(
        payload.get("refresh_token_expires_in")
    ) or _normalize_text(previous.get("refresh_token_expiry", ""))

    return {
        "version": previous.get("version", 1),
        "base_url": _normalize_base_url(previous.get("base_url", "")),
        "client_id": _normalize_text(previous.get("client_id", ""))
        or "hyperbrowser-cli",
        "token_type": token_type,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expiry": expiry,
        "scope": _normalize_text(_string_value(payload.get("scope")))
        or _normalize_text(previous.get("scope", "")),
        "refresh_token_expiry": refresh_expiry,
    }


def _write_oauth_session_atomic(session_path: Path, session: Dict[str, str]) -> None:
    session_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(session_path.parent, 0o700)
    except OSError:
        pass

    payload = f"{json.dumps(session, indent=2)}\n"
    fd, temp_path = tempfile.mkstemp(
        prefix=f"{session_path.name}.",
        suffix=".tmp",
        dir=str(session_path.parent),
    )
    renamed = False
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, session_path)
        renamed = True
        try:
            os.chmod(session_path, 0o600)
        except OSError:
            pass
    finally:
        if not renamed:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _should_use_oauth_session(
    session: Dict[str, str],
    force_refresh: bool,
    rejected_access_token: Optional[str],
) -> bool:
    if not _is_access_token_usable(session):
        return False
    if not force_refresh:
        return True
    return _normalize_text(session.get("access_token", "")) != _normalize_text(
        rejected_access_token or ""
    )


def _is_access_token_usable(session: Dict[str, str]) -> bool:
    expiry = _parse_timestamp(session.get("expiry"))
    if expiry is None or _normalize_text(session.get("access_token", "")) == "":
        return False
    return (expiry * 1000) - (time.time() * 1000) > OAUTH_REFRESH_EARLY_EXPIRY_MS


def _is_refresh_token_expired(session: Dict[str, str]) -> bool:
    expiry = _parse_timestamp(session.get("refresh_token_expiry"))
    if expiry is None:
        return False
    return (expiry * 1000) <= (time.time() * 1000)


def _redact_refresh_error_details(payload: Any) -> Any:
    if isinstance(payload, dict):
        redacted: Dict[str, Any] = {}
        for key, value in payload.items():
            if key in {"access_token", "refresh_token"}:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_refresh_error_details(value)
        return redacted
    if isinstance(payload, list):
        return [_redact_refresh_error_details(value) for value in payload]
    return payload


def _derive_expiry(value: object) -> Optional[str]:
    if isinstance(value, (int, float)) and value > 0:
        return (
            datetime.now(timezone.utc) + timedelta(seconds=float(value))
        ).isoformat()
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
        if parsed > 0:
            return (datetime.now(timezone.utc) + timedelta(seconds=parsed)).isoformat()
    return None


def _parse_timestamp(value: Optional[str]) -> Optional[float]:
    normalized = _normalize_text(value or "")
    if normalized == "":
        return None
    try:
        adjusted = normalized.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(adjusted)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _normalize_positive_int(
    explicit_value: Optional[int], env_value: Optional[str], fallback: int
) -> int:
    if explicit_value is not None and explicit_value > 0:
        return explicit_value
    if env_value:
        try:
            parsed = int(env_value)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
    return fallback


def _normalize_profile(value: str) -> str:
    normalized = _normalize_text(value) or DEFAULT_PROFILE
    if not PROFILE_NAME_PATTERN.fullmatch(normalized):
        raise HyperbrowserError(
            "Invalid Hyperbrowser profile name",
            code="invalid_profile",
            retryable=False,
            service="control",
        )
    return normalized


def _normalize_base_url(value: Optional[str]) -> str:
    normalized = _normalize_text(value or "")
    if normalized == "":
        return ""
    normalized = normalized.rstrip("/")
    if normalized.endswith("/api"):
        normalized = normalized[: -len("/api")]
    return normalized.rstrip("/")


def _normalize_text(value: str) -> str:
    return value.strip()


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""
