from dataclasses import dataclass
import json
from typing import Dict, Mapping, Optional
import os

from .exceptions import HyperbrowserError


@dataclass
class ClientConfig:
    """Configuration for the Hyperbrowser client"""

    api_key: str
    base_url: str = "https://api.hyperbrowser.ai"
    headers: Optional[Mapping[str, str]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str):
            raise HyperbrowserError("api_key must be a string")
        if not isinstance(self.base_url, str):
            raise HyperbrowserError("base_url must be a string")
        if self.headers is not None and not isinstance(self.headers, Mapping):
            raise HyperbrowserError("headers must be a mapping of string pairs")
        self.api_key = self.api_key.strip()
        if not self.api_key:
            raise HyperbrowserError("api_key must not be empty")
        self.base_url = self.base_url.strip().rstrip("/")
        if not self.base_url:
            raise HyperbrowserError("base_url must not be empty")
        if not (
            self.base_url.startswith("https://") or self.base_url.startswith("http://")
        ):
            raise HyperbrowserError("base_url must start with 'https://' or 'http://'")
        if self.headers is not None:
            normalized_headers: Dict[str, str] = {}
            for key, value in self.headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise HyperbrowserError("headers must be a mapping of string pairs")
                normalized_headers[key] = value
            self.headers = normalized_headers

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
        headers = cls.parse_headers_from_env(os.environ.get("HYPERBROWSER_HEADERS"))
        return cls(api_key=api_key, base_url=base_url, headers=headers)

    @staticmethod
    def parse_headers_from_env(raw_headers: Optional[str]) -> Optional[Dict[str, str]]:
        if raw_headers is None or not raw_headers.strip():
            return None
        try:
            parsed_headers = json.loads(raw_headers)
        except json.JSONDecodeError as exc:
            raise HyperbrowserError(
                "HYPERBROWSER_HEADERS must be valid JSON object"
            ) from exc
        if not isinstance(parsed_headers, dict):
            raise HyperbrowserError(
                "HYPERBROWSER_HEADERS must be a JSON object of string pairs"
            )
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in parsed_headers.items()
        ):
            raise HyperbrowserError(
                "HYPERBROWSER_HEADERS must be a JSON object of string pairs"
            )
        return parsed_headers
