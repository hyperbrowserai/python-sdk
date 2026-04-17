import os
from dataclasses import replace
from typing import Optional

from ..control_auth import DEFAULT_BASE_URL, resolve_control_plane_config
from ..config import ClientConfig
from ..transport.base import TransportStrategy


class HyperbrowserBase:
    """Base class with shared functionality for sync/async clients"""

    def __init__(
        self,
        transport: TransportStrategy,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        runtime_proxy_override: Optional[str] = None,
    ):
        if config is None:
            config = ClientConfig(
                api_key=api_key if api_key is not None else os.environ.get("HYPERBROWSER_API_KEY"),
                base_url=(
                    base_url
                    if base_url is not None
                    else os.environ.get("HYPERBROWSER_BASE_URL", DEFAULT_BASE_URL)
                ),
                profile=os.environ.get("HYPERBROWSER_PROFILE"),
                runtime_proxy_override=runtime_proxy_override,
            )

        resolved_base_url, auth = resolve_control_plane_config(config)
        self.config = replace(config, base_url=resolved_base_url)
        self.auth = auth
        self.transport = transport(auth)

    def _build_url(self, path: str) -> str:
        return f"{self.config.base_url}/api{path}"
