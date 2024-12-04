from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ClientConfig:
    """Configuration for the Hyperbrowser client"""

    api_key: str
    base_url: str = "https://api.hyperbrowser.com"

    @classmethod
    def from_env(cls) -> "ClientConfig":
        api_key = os.environ.get("HYPERBROWSER_API_KEY")
        if api_key is None:
            raise ValueError("HYPERBROWSER_API_KEY environment variable is required")

        base_url = os.environ.get(
            "HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.com"
        )
        return cls(api_key=api_key, base_url=base_url)
