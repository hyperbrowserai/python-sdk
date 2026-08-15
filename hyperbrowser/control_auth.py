import asyncio
import functools
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import urlencode

import httpx

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_FRONTEND_BASE_URL,
    ClientConfig,
)
from .exceptions import HyperbrowserError
from .sandbox_common import parse_error_payload

DEFAULT_PROFILE = "default"
LEGACY_DEFAULT_BASE_URL = "https://app.hyperbrowser.ai"
DEFAULT_LOCK_TIMEOUT_MS = 30000
DEFAULT_LOCK_POLL_INTERVAL_MS = 125
DEFAULT_LOCK_STALE_MS = 120000
DEFAULT_OAUTH_REFRESH_TIMEOUT_S = 30.0
OAUTH_REFRESH_EARLY_EXPIRY_MS = 30000
PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
ISO_TIMESTAMP_PATTERN = re.compile(
    r"^(?P<head>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    r"(?P<frac>\.\d+)?"
    r"(?P<tz>Z|[+-]\d{2}:?\d{2})?$",
    re.IGNORECASE,
)
TERMINAL_OAUTH_REFRESH_ERRORS = {
    "invalid_grant",
    "invalid_client",
    "unauthorized_client",
}


@dataclass
class _OAuthSettings:
    profile: str
    session_path: Path
    lock_path: Path
    base_url: str
    token_url: str
    refresh_timeout_s: float = DEFAULT_OAUTH_REFRESH_TIMEOUT_S
    lock_timeout_ms: int = DEFAULT_LOCK_TIMEOUT_MS
    lock_poll_interval_ms: int = DEFAULT_LOCK_POLL_INTERVAL_MS
    lock_stale_ms: int = DEFAULT_LOCK_STALE_MS
    cached_session: Optional[Dict[str, Any]] = field(default=None)
    cached_mtime_ns: Optional[int] = field(default=None)


class ControlPlaneAuthManager:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        oauth: Optional[_OAuthSettings] = None,
    ):
        if api_key is None and oauth is None:
            raise ValueError("api_key or oauth settings are required")
        self._api_key = api_key
        self._oauth = oauth

    @classmethod
    def for_api_key(cls, api_key: str) -> "ControlPlaneAuthManager":
        return cls(api_key=api_key)

    @property
    def is_oauth(self) -> bool:
        return self._oauth is not None

    def authorize_headers(
        self,
        *,
        force_refresh: bool = False,
        rejected_access_token: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Optional[str]]:
        if self._api_key is not None:
            return {"x-api-key": self._api_key}, None

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
        if self._api_key is not None:
            return self.authorize_headers()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(
                self.authorize_headers,
                force_refresh=force_refresh,
                rejected_access_token=rejected_access_token,
            ),
        )

    def _resolve_oauth_access_token(
        self,
        *,
        force_refresh: bool,
        rejected_access_token: Optional[str],
    ) -> str:
        session, session_mtime_ns = self._load_oauth_session_with_mtime()
        if _should_use_oauth_session(session, force_refresh, rejected_access_token):
            return _normalize_text(session["access_token"])

        oauth = self._oauth
        deadline = time.monotonic() + (oauth.lock_timeout_ms / 1000.0)
        while True:
            lock_fd = self._try_acquire_rotation_lock()
            if lock_fd is not None:
                try:
                    return self._refresh_oauth_access_token_locked(
                        force_refresh=force_refresh,
                        rejected_access_token=rejected_access_token,
                    )
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

            time.sleep(oauth.lock_poll_interval_ms / 1000.0)
            updated = self._load_updated_oauth_session(session_mtime_ns)
            if updated is None:
                continue
            session, session_mtime_ns = updated
            if _should_use_oauth_session(session, True, rejected_access_token):
                return _normalize_text(session["access_token"])
            if _is_refresh_token_expired(session):
                raise _oauth_session_expired_error()

    def _refresh_oauth_access_token_locked(
        self,
        *,
        force_refresh: bool,
        rejected_access_token: Optional[str],
    ) -> str:
        session, _ = self._load_oauth_session_with_mtime()
        if _should_use_oauth_session(session, force_refresh, rejected_access_token):
            return _normalize_text(session["access_token"])
        if _is_refresh_token_expired(session):
            self._expire_oauth_session(session)
            raise _oauth_session_expired_error()
        refreshed = self._refresh_oauth_session(session)
        return _normalize_text(refreshed["access_token"])

    def _load_oauth_session_with_mtime(self) -> Tuple[Dict[str, Any], Optional[int]]:
        oauth = self._oauth
        mtime_ns = self._get_session_mtime_ns()
        if oauth.cached_session is not None and oauth.cached_mtime_ns == mtime_ns:
            return oauth.cached_session, mtime_ns

        session = self._read_oauth_session()
        oauth.cached_session = session
        oauth.cached_mtime_ns = mtime_ns
        return session, mtime_ns

    def _read_oauth_session(self) -> Dict[str, Any]:
        session_path = self._oauth.session_path
        try:
            raw = session_path.read_text()
        except FileNotFoundError:
            raise _oauth_session_expired_error()
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

        _validate_oauth_session(session, expected_base_url=self._oauth.base_url)
        return session

    def _load_updated_oauth_session(
        self, previous_mtime_ns: Optional[int]
    ) -> Optional[Tuple[Dict[str, Any], Optional[int]]]:
        current_mtime_ns = self._get_session_mtime_ns()
        if current_mtime_ns == previous_mtime_ns:
            return None
        self._oauth.cached_session = None
        self._oauth.cached_mtime_ns = None
        return self._load_oauth_session_with_mtime()

    def _get_session_mtime_ns(self) -> Optional[int]:
        try:
            return self._oauth.session_path.stat().st_mtime_ns
        except FileNotFoundError:
            raise _oauth_session_expired_error()
        except OSError as error:
            raise HyperbrowserError(
                "Failed to inspect saved OAuth session",
                code="oauth_session_read_failed",
                retryable=False,
                service="control",
                cause=error,
                original_error=error,
            )

    def _refresh_oauth_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=self._oauth.refresh_timeout_s) as client:
                response = client.post(
                    self._oauth.token_url,
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
        self, session: Dict[str, Any], response: httpx.Response
    ) -> Dict[str, Any]:
        fallback = f"OAuth refresh failed with status {response.status_code}"
        message, code, details = parse_error_payload(response.text, fallback)

        if response.status_code >= 400:
            error_code = _normalize_text(code)
            if isinstance(details, dict):
                error_code = error_code or _normalize_text(details.get("error"))
                message = (
                    _normalize_text(details.get("error_description"))
                    or _normalize_text(details.get("message"))
                    or message
                )
            if error_code in TERMINAL_OAUTH_REFRESH_ERRORS:
                self._expire_oauth_session(session)
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                code=error_code or "oauth_refresh_failed",
                retryable=False,
                service="control",
                details=_redact_refresh_error_details(details),
                response=response,
            )

        payload = details if isinstance(details, dict) else {}
        if not payload and response.text:
            try:
                parsed = response.json()
            except ValueError:
                parsed = {}
            payload = parsed if isinstance(parsed, dict) else {}

        refreshed = _build_refreshed_oauth_session(session, payload)
        _write_oauth_session_atomic(self._oauth.session_path, refreshed)
        try:
            mtime_ns = self._oauth.session_path.stat().st_mtime_ns
        except OSError:
            mtime_ns = None
        self._oauth.cached_session = refreshed
        self._oauth.cached_mtime_ns = mtime_ns
        return refreshed

    def _try_acquire_rotation_lock(self) -> Optional[int]:
        lock_path = self._oauth.lock_path
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
                lock_path.unlink()
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
        lock_path = self._oauth.lock_path
        try:
            fd = os.open(str(lock_path), os.O_RDONLY)
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

        try:
            file_stat = os.fstat(fd)
            if not _is_rotation_lock_stale(file_stat, self._oauth.lock_stale_ms):
                return
            try:
                path_stat = os.stat(str(lock_path))
            except FileNotFoundError:
                return
            if not _same_lock_identity(file_stat, path_stat):
                return
            os.unlink(str(lock_path))
        except FileNotFoundError:
            return
        except OSError:
            return
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _release_rotation_lock(self, lock_fd: int) -> None:
        try:
            os.close(lock_fd)
        except OSError:
            pass
        try:
            self._oauth.lock_path.unlink()
        except OSError:
            pass

    def _expire_oauth_session(self, session: Dict[str, Any]) -> None:
        current = _try_load_oauth_session(self._oauth.session_path)
        if current is None:
            self._oauth.cached_session = None
            self._oauth.cached_mtime_ns = None
            return
        if _normalize_text(current.get("refresh_token")) != _normalize_text(
            session.get("refresh_token")
        ) or _normalize_text(current.get("access_token")) != _normalize_text(
            session.get("access_token")
        ):
            return
        try:
            self._oauth.session_path.unlink()
        except OSError:
            pass
        self._oauth.cached_session = None
        self._oauth.cached_mtime_ns = None


def coerce_transport_auth(
    auth: Union[str, ControlPlaneAuthManager],
) -> ControlPlaneAuthManager:
    if isinstance(auth, ControlPlaneAuthManager):
        return auth
    if isinstance(auth, str):
        return ControlPlaneAuthManager.for_api_key(auth)
    raise TypeError("auth must be a ControlPlaneAuthManager or API key string")


def resolve_control_plane_config(
    config: ClientConfig,
) -> Tuple[str, ControlPlaneAuthManager]:
    if not _normalize_text(config.base_url):
        raise HyperbrowserError(
            "A base URL must be provided",
            code="invalid_base_url",
            retryable=False,
            service="control",
        )

    if config.api_key is not None:
        api_key = _normalize_text(config.api_key)
        if api_key == "":
            raise HyperbrowserError(
                "API key must be provided",
                code="missing_auth",
                retryable=False,
                service="control",
            )
        return config.base_url, ControlPlaneAuthManager.for_api_key(api_key)

    profile = _normalize_profile(config.profile or DEFAULT_PROFILE)
    session_path = _resolve_oauth_session_path(profile)
    session = _try_load_oauth_session(session_path)
    if session is None:
        raise HyperbrowserError(
            "API key must be provided or an OAuth session must be saved with hx auth login",
            code="missing_auth",
            retryable=False,
            service="control",
        )

    session_base_url = _normalize_control_base_url(session.get("base_url"))
    if _is_default_control_base_url(config.base_url):
        resolved_base_url = session_base_url or DEFAULT_BASE_URL
    elif _oauth_base_urls_match(config.base_url, session_base_url):
        resolved_base_url = _normalize_control_base_url(config.base_url)
    else:
        raise HyperbrowserError(
            f"Saved OAuth session for profile {profile} targets {_normalize_base_url(session.get('base_url'))}, not {config.base_url}",
            code="oauth_base_url_mismatch",
            retryable=False,
            service="control",
        )

    frontend_base_url = resolve_frontend_base_url(
        resolved_base_url,
        config.frontend_url,
    )
    try:
        cached_mtime_ns = session_path.stat().st_mtime_ns
    except OSError:
        cached_mtime_ns = None

    return resolved_base_url, ControlPlaneAuthManager(
        oauth=_OAuthSettings(
            profile=profile,
            session_path=session_path,
            lock_path=Path(f"{session_path}.refresh.lock"),
            base_url=resolved_base_url,
            token_url=f"{frontend_base_url}/oauth/token",
            refresh_timeout_s=DEFAULT_OAUTH_REFRESH_TIMEOUT_S,
            lock_timeout_ms=_positive_or_default(
                config.auth_lock_timeout_ms, DEFAULT_LOCK_TIMEOUT_MS
            ),
            lock_poll_interval_ms=_positive_or_default(
                config.auth_lock_poll_interval_ms, DEFAULT_LOCK_POLL_INTERVAL_MS
            ),
            lock_stale_ms=_positive_or_default(
                config.auth_lock_stale_ms, DEFAULT_LOCK_STALE_MS
            ),
            cached_session=session,
            cached_mtime_ns=cached_mtime_ns,
        )
    )


def resolve_frontend_base_url(
    control_base_url: str,
    explicit_frontend_url: Optional[str] = None,
) -> str:
    explicit = _normalize_base_url(explicit_frontend_url)
    if explicit:
        return explicit
    if _is_default_control_base_url(control_base_url):
        return DEFAULT_FRONTEND_BASE_URL
    return _normalize_base_url(control_base_url) or DEFAULT_FRONTEND_BASE_URL


def _oauth_session_expired_error() -> HyperbrowserError:
    return HyperbrowserError(
        "OAuth session refresh token expired",
        code="oauth_session_expired",
        retryable=False,
        service="control",
    )


def _resolve_oauth_session_path(profile: str) -> Path:
    return Path.home() / ".hx_config" / "auth" / f"{profile}.json"


def _try_load_oauth_session(session_path: Path) -> Optional[Dict[str, Any]]:
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
    session: Any, expected_base_url: Optional[str] = None
) -> None:
    if not isinstance(session, dict):
        raise HyperbrowserError(
            "Saved OAuth session is invalid",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )

    access_token = _normalize_text(session.get("access_token"))
    refresh_token = _normalize_text(session.get("refresh_token"))
    base_url = _normalize_base_url(session.get("base_url"))

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
    expiry_text = _normalize_text(session.get("expiry"))
    if expiry_text and _parse_timestamp(expiry_text) is None:
        raise HyperbrowserError(
            "Saved OAuth session has an invalid expiry",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )

    refresh_expiry = _normalize_text(session.get("refresh_token_expiry"))
    if refresh_expiry and _parse_timestamp(refresh_expiry) is None:
        raise HyperbrowserError(
            "Saved OAuth session has an invalid refresh token expiry",
            code="oauth_session_invalid",
            retryable=False,
            service="control",
        )

    if expected_base_url and not _oauth_base_urls_match(base_url, expected_base_url):
        raise HyperbrowserError(
            "Saved OAuth session targets a different base URL",
            code="oauth_base_url_mismatch",
            retryable=False,
            service="control",
        )


def _build_refresh_form(session: Dict[str, Any]) -> str:
    return urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": _normalize_text(session.get("client_id"))
            or "hyperbrowser-cli",
            "refresh_token": _normalize_text(session.get("refresh_token")),
        }
    )


def _build_refreshed_oauth_session(
    previous: Dict[str, Any], payload: Dict[str, object]
) -> Dict[str, Any]:
    access_token = _normalize_text(payload.get("access_token"))
    if access_token == "":
        raise HyperbrowserError(
            "OAuth refresh response did not include an access token",
            code="oauth_refresh_failed",
            retryable=False,
            service="control",
            details=payload,
        )

    return {
        "version": previous.get("version", 1),
        "base_url": _normalize_base_url(previous.get("base_url")),
        "client_id": _normalize_text(previous.get("client_id")) or "hyperbrowser-cli",
        "token_type": _normalize_text(payload.get("token_type"))
        or _normalize_text(previous.get("token_type"))
        or "Bearer",
        "access_token": access_token,
        "refresh_token": _normalize_text(payload.get("refresh_token"))
        or _normalize_text(previous.get("refresh_token")),
        "expiry": _derive_expiry(payload.get("expires_in")) or "",
        "scope": _normalize_text(payload.get("scope"))
        or _normalize_text(previous.get("scope")),
        "refresh_token_expiry": _derive_expiry(payload.get("refresh_token_expires_in"))
        or _normalize_text(previous.get("refresh_token_expiry")),
    }


def _write_oauth_session_atomic(session_path: Path, session: Dict[str, Any]) -> None:
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
        _try_fchmod(fd, 0o600)
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
    session: Dict[str, Any],
    force_refresh: bool,
    rejected_access_token: Optional[str],
) -> bool:
    if not _is_access_token_usable(session):
        return False
    if not force_refresh:
        return True
    return _normalize_text(session.get("access_token")) != _normalize_text(
        rejected_access_token
    )


def _is_access_token_usable(session: Dict[str, Any]) -> bool:
    if _normalize_text(session.get("access_token")) == "":
        return False
    expiry = _parse_timestamp(session.get("expiry"))
    if expiry is None:
        return True
    return (expiry * 1000) - (time.time() * 1000) > OAUTH_REFRESH_EARLY_EXPIRY_MS


def _is_refresh_token_expired(session: Dict[str, Any]) -> bool:
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


def _parse_timestamp(value: Optional[object]) -> Optional[float]:
    normalized = _normalize_text(value)
    if normalized == "":
        return None
    parsed = _parse_iso_datetime(normalized)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    match = ISO_TIMESTAMP_PATTERN.fullmatch(value)
    if match is None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    head = match.group("head").replace(" ", "T")
    frac = match.group("frac") or ""
    tz = match.group("tz") or ""
    if frac:
        frac = "." + frac[1:7].ljust(6, "0")
    if tz.upper() == "Z":
        tz = "+00:00"
    elif len(tz) == 5 and tz[0] in "+-":
        tz = f"{tz[:3]}:{tz[3:]}"

    try:
        return datetime.fromisoformat(f"{head}{frac}{tz}")
    except ValueError:
        return None


def _is_rotation_lock_stale(stat_result, stale_ms: int) -> bool:
    return (time.time() * 1000) - (stat_result.st_mtime * 1000) >= stale_ms


def _same_lock_identity(left, right) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _try_fchmod(fd: int, mode: int) -> None:
    setter = getattr(os, "fchmod", None)
    if setter is None:
        return
    try:
        setter(fd, mode)
    except (NotImplementedError, OSError):
        pass


def _positive_or_default(value: Optional[int], default: int) -> int:
    if value is not None and value > 0:
        return value
    return default


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


def _normalize_base_url(value: Optional[object]) -> str:
    normalized = _normalize_text(value)
    if normalized == "":
        return ""
    normalized = normalized.rstrip("/")
    if normalized.endswith("/api"):
        normalized = normalized[: -len("/api")]
    return normalized.rstrip("/")


def _normalize_control_base_url(value: Optional[object]) -> str:
    normalized = _normalize_base_url(value)
    if normalized == LEGACY_DEFAULT_BASE_URL:
        return DEFAULT_BASE_URL
    return normalized


def _is_default_control_base_url(value: Optional[object]) -> bool:
    normalized = _normalize_base_url(value)
    return normalized in {DEFAULT_BASE_URL, LEGACY_DEFAULT_BASE_URL}


def _oauth_base_urls_match(left: Optional[object], right: Optional[object]) -> bool:
    normalized_left = _normalize_base_url(left)
    normalized_right = _normalize_base_url(right)
    if normalized_left == "" or normalized_right == "":
        return False
    if normalized_left == normalized_right:
        return True
    return _is_default_control_base_url(
        normalized_left
    ) and _is_default_control_base_url(normalized_right)


def _normalize_text(value: Optional[object]) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
