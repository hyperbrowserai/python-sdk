from dataclasses import dataclass
from typing import Optional
import os


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
    base_url: str = "https://api.hyperbrowser.ai"
    runtime_proxy_override: Optional[str] = None
    profile: Optional[str] = None
    frontend_url: Optional[str] = None
    auth_lock_timeout_ms: Optional[int] = None
    auth_lock_poll_interval_ms: Optional[int] = None
    auth_lock_stale_ms: Optional[int] = None

    @classmethod
    def from_env(cls) -> "ClientConfig":
        api_key = os.environ.get("HYPERBROWSER_API_KEY")
        if api_key is None:
            raise ValueError("HYPERBROWSER_API_KEY environment variable is required")

        return cls(
            api_key=api_key,
            base_url=os.environ.get(
                "HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.ai"
            ),
            profile=os.environ.get("HYPERBROWSER_PROFILE"),
            frontend_url=os.environ.get("HYPERBROWSER_FRONTEND_URL"),
            auth_lock_timeout_ms=_env_positive_int("HYPERBROWSER_AUTH_LOCK_TIMEOUT_MS"),
            auth_lock_poll_interval_ms=_env_positive_int(
                "HYPERBROWSER_AUTH_LOCK_POLL_INTERVAL_MS"
            ),
            auth_lock_stale_ms=_env_positive_int("HYPERBROWSER_AUTH_LOCK_STALE_MS"),
        )
