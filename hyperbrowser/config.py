from dataclasses import dataclass
from typing import Optional
import os

DEFAULT_BASE_URL = "https://api.hyperbrowser.ai"
DEFAULT_FRONTEND_BASE_URL = "https://app.hyperbrowser.ai"


def _env_text(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _env_positive_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


@dataclass
class ClientConfig:
    """Configuration for the Hyperbrowser client"""

    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    runtime_proxy_override: Optional[str] = None
    profile: Optional[str] = None
    frontend_url: Optional[str] = None
    auth_lock_timeout_ms: Optional[int] = None
    auth_lock_poll_interval_ms: Optional[int] = None
    auth_lock_stale_ms: Optional[int] = None

    @classmethod
    def from_constructor(
        cls,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        runtime_proxy_override: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> "ClientConfig":
        return cls(
            api_key=api_key
            if api_key is not None
            else _env_text("HYPERBROWSER_API_KEY"),
            base_url=(
                base_url
                if base_url is not None
                else (_env_text("HYPERBROWSER_BASE_URL") or DEFAULT_BASE_URL)
            ),
            runtime_proxy_override=runtime_proxy_override,
            profile=(
                profile if profile is not None else _env_text("HYPERBROWSER_PROFILE")
            ),
            frontend_url=_env_text("HYPERBROWSER_FRONTEND_URL"),
            auth_lock_timeout_ms=_env_positive_int("HYPERBROWSER_AUTH_LOCK_TIMEOUT_MS"),
            auth_lock_poll_interval_ms=_env_positive_int(
                "HYPERBROWSER_AUTH_LOCK_POLL_INTERVAL_MS"
            ),
            auth_lock_stale_ms=_env_positive_int("HYPERBROWSER_AUTH_LOCK_STALE_MS"),
        )

    @classmethod
    def from_env(cls) -> "ClientConfig":
        api_key = _env_text("HYPERBROWSER_API_KEY")
        if api_key is None:
            raise ValueError("HYPERBROWSER_API_KEY environment variable is required")
        return cls.from_constructor(api_key=api_key)
