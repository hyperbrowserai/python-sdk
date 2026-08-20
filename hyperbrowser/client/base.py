from dataclasses import replace
from typing import Optional

from ..config import ClientConfig
from ..control_auth import resolve_control_plane_config
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
        profile: Optional[str] = None,
    ):
        if config is None:
            config = ClientConfig.from_constructor(
                api_key=api_key,
                base_url=base_url,
                runtime_proxy_override=runtime_proxy_override,
                profile=profile,
            )

        resolved_base_url, auth = resolve_control_plane_config(config)
        self.config = replace(config, base_url=resolved_base_url)
        self.auth = auth
        self.transport = transport(auth)

    def _build_url(self, path: str) -> str:
        return f"{self.config.base_url}/api{path}"
