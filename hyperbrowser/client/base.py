from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from ..config import ClientConfig
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
    ):
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
                        "HYPERBROWSER_BASE_URL", "https://app.hyperbrowser.ai"
                    )
                ),
            )

        if not config.api_key:
            raise HyperbrowserError("API key must be provided")

        self.config = config
        self.transport = transport(config.api_key)

    def _build_url(self, path: str) -> str:
        return f"{self.config.base_url}/api{path}"
