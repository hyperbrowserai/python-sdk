import os
from urllib.parse import urlparse
from typing import Mapping, Optional, Type, Union

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
        headers: Optional[Mapping[str, str]] = None,
    ):
        if config is not None and any(
            value is not None for value in (api_key, base_url, headers)
        ):
            raise TypeError(
                "Pass either `config` or `api_key`/`base_url`/`headers`, not both."
            )

        if config is None:
            resolved_api_key = (
                api_key
                if api_key is not None
                else os.environ.get("HYPERBROWSER_API_KEY")
            )
            if resolved_api_key is None:
                raise HyperbrowserError(
                    "API key must be provided via `api_key` or HYPERBROWSER_API_KEY"
                )
            if not isinstance(resolved_api_key, str):
                raise HyperbrowserError("api_key must be a string")
            if not resolved_api_key.strip():
                raise HyperbrowserError(
                    "API key must be provided via `api_key` or HYPERBROWSER_API_KEY"
                )
            resolved_headers = (
                headers
                if headers is not None
                else ClientConfig.parse_headers_from_env(
                    os.environ.get("HYPERBROWSER_HEADERS")
                )
            )
            config = ClientConfig(
                api_key=resolved_api_key,
                base_url=(
                    base_url
                    if base_url is not None
                    else os.environ.get(
                        "HYPERBROWSER_BASE_URL", "https://api.hyperbrowser.ai"
                    )
                ),
                headers=resolved_headers,
            )

        if not config.api_key:
            raise HyperbrowserError("API key must be provided")

        self.config = config
        self.transport = transport(config.api_key, headers=config.headers)

    def _build_url(self, path: str) -> str:
        if not isinstance(path, str):
            raise HyperbrowserError("path must be a string")
        stripped_path = path.strip()
        if not stripped_path:
            raise HyperbrowserError("path must not be empty")
        if "\\" in stripped_path:
            raise HyperbrowserError("path must not contain backslashes")
        parsed_path = urlparse(stripped_path)
        if parsed_path.scheme:
            raise HyperbrowserError("path must be a relative API path")
        if parsed_path.fragment:
            raise HyperbrowserError("path must not include URL fragments")
        normalized_path = f"/{stripped_path.lstrip('/')}"
        base_has_api_suffix = (
            urlparse(self.config.base_url).path.rstrip("/").endswith("/api")
        )

        if normalized_path == "/api" or normalized_path.startswith("/api/"):
            if base_has_api_suffix:
                deduped_path = normalized_path[len("/api") :]
                return f"{self.config.base_url}{deduped_path}"
            return f"{self.config.base_url}{normalized_path}"

        if base_has_api_suffix:
            return f"{self.config.base_url}{normalized_path}"
        return f"{self.config.base_url}/api{normalized_path}"
