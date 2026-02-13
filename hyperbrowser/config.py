from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Dict, Mapping, Optional
import os

from .exceptions import HyperbrowserError
from .header_utils import normalize_headers, parse_headers_env_json


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
        self.api_key = self.api_key.strip()
        if not self.api_key:
            raise HyperbrowserError("api_key must not be empty")
        self.base_url = self.base_url.strip().rstrip("/")
        if not self.base_url:
            raise HyperbrowserError("base_url must not be empty")
        parsed_base_url = urlparse(self.base_url)
        if (
            parsed_base_url.scheme not in {"https", "http"}
            or not parsed_base_url.netloc
        ):
            raise HyperbrowserError(
                "base_url must start with 'https://' or 'http://' and include a host"
            )
        if parsed_base_url.query or parsed_base_url.fragment:
            raise HyperbrowserError(
                "base_url must not include query parameters or fragments"
            )
        self.headers = normalize_headers(
            self.headers,
            mapping_error_message="headers must be a mapping of string pairs",
        )

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
        return parse_headers_env_json(raw_headers)
