from dataclasses import dataclass
from typing import Dict, Optional
import os

from .exceptions import HyperbrowserError


@dataclass
class ClientConfig:
    """Configuration for the Hyperbrowser client"""

    api_key: str
    base_url: str = "https://api.hyperbrowser.ai"
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str):
            raise HyperbrowserError("api_key must be a string")
        if not isinstance(self.base_url, str):
            raise HyperbrowserError("base_url must be a string")
        self.api_key = self.api_key.strip()
        self.base_url = self.base_url.strip().rstrip("/")

    @classmethod
    def from_env(cls) -> "ClientConfig":
        api_key = os.environ.get("HYPERBROWSER_API_KEY")
        if api_key is None or not api_key.strip():
            raise HyperbrowserError(
                "HYPERBROWSER_API_KEY environment variable is required"
            )

        base_url = os.environ.get(
            "HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.ai"
        )
        return cls(api_key=api_key, base_url=base_url)
