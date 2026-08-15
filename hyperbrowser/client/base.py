from dataclasses import replace
from typing import Optional

from ..config import ClientConfig, _env_positive_int
from ..control_auth import DEFAULT_BASE_URL, resolve_control_plane_config
from ..transport.base import TransportStrategy
import os


class HyperbrowserBase:
    """Base class with shared functionality for sync/async clients"""

    def __init__(
        self,
        transport: TransportStrategy,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        runtime_proxy_override: Optional[str] = None,
        profile: Optional[str] = None,
    ):
        if config is None:
            config = ClientConfig(
                api_key=(
                    api_key
                    if api_key is not None
                    else os.environ.get("HYPERBROWSER_API_KEY")
                ),
                base_url=(
                    base_url
                    if base_url is not None
                    else os.environ.get("HYPERBROWSER_BASE_URL", DEFAULT_BASE_URL)
                ),
                runtime_proxy_override=runtime_proxy_override,
                profile=(
                    profile
                    if profile is not None
                    else os.environ.get("HYPERBROWSER_PROFILE")
                ),
                frontend_url=os.environ.get("HYPERBROWSER_FRONTEND_URL"),
                auth_lock_timeout_ms=_env_positive_int(
                    "HYPERBROWSER_AUTH_LOCK_TIMEOUT_MS"
                ),
                auth_lock_poll_interval_ms=_env_positive_int(
                    "HYPERBROWSER_AUTH_LOCK_POLL_INTERVAL_MS"
                ),
                auth_lock_stale_ms=_env_positive_int("HYPERBROWSER_AUTH_LOCK_STALE_MS"),
            )

        resolved_base_url, auth = resolve_control_plane_config(config)
        self.config = replace(config, base_url=resolved_base_url)
        self.auth = auth
        self.transport = transport(auth)

    def _build_url(self, path: str) -> str:
        return f"{self.config.base_url}/api{path}"
