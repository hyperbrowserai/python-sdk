import os
from typing import Dict, Optional, Type, Union

from hyperbrowser.exceptions import HyperbrowserError
from ..config import ClientConfig
from ..transport.base import AsyncTransportStrategy, SyncTransportStrategy


class HyperbrowserBase:
    """Base class with shared functionality for sync/async clients"""

    def __init__(
        self,
        transport: Type[Union[SyncTransportStrategy, AsyncTransportStrategy]],
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        if config is not None and any(
            value is not None for value in (api_key, base_url, headers)
        ):
            raise TypeError(
                "Pass either `config` or `api_key`/`base_url`/`headers`, not both."
            )

        if config is None:
            config = ClientConfig(
                api_key=(
                    api_key
                    if api_key is not None
                    else os.environ.get("HYPERBROWSER_API_KEY", "")
                ),
                base_url=(
                    base_url
                    if base_url is not None
                    else os.environ.get(
                        "HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.ai"
                    )
                ),
                headers=headers,
            )

        if not config.api_key:
            raise HyperbrowserError("API key must be provided")

        self.config = config
        self.transport = transport(config.api_key, headers=config.headers)

    def _build_url(self, path: str) -> str:
        return f"{self.config.base_url}/api{path}"
