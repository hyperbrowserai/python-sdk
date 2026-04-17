import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClientConfig:
    """Configuration for the Hyperbrowser client"""

    api_key: Optional[str] = None
    base_url: str = "https://api.hyperbrowser.ai"
    profile: Optional[str] = None
    auth_lock_timeout_ms: Optional[int] = None
    auth_lock_poll_interval_ms: Optional[int] = None
    auth_lock_stale_ms: Optional[int] = None
    runtime_proxy_override: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ClientConfig":
        return cls(
            api_key=os.environ.get("HYPERBROWSER_API_KEY"),
            base_url=os.environ.get(
                "HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.ai"
            ),
            profile=os.environ.get("HYPERBROWSER_PROFILE"),
        )
