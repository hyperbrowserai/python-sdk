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
            raise HyperbrowserError(
                "Pass either `config` or `api_key`/`base_url`/`headers`, not both."
            )

        if config is None:
            api_key_from_constructor = api_key is not None
            resolved_api_key = (
                api_key
                if api_key_from_constructor
                else os.environ.get("HYPERBROWSER_API_KEY")
            )
            if resolved_api_key is None:
                raise HyperbrowserError(
                    "API key must be provided via `api_key` or HYPERBROWSER_API_KEY"
                )
            if not isinstance(resolved_api_key, str):
                raise HyperbrowserError("api_key must be a string")
            try:
                normalized_resolved_api_key = resolved_api_key.strip()
                if not isinstance(normalized_resolved_api_key, str):
                    raise TypeError("normalized api_key must be a string")
            except HyperbrowserError:
                raise
            except Exception as exc:
                raise HyperbrowserError(
                    "Failed to normalize api_key",
                    original_error=exc,
                ) from exc
            if not normalized_resolved_api_key:
                if api_key_from_constructor:
                    raise HyperbrowserError("api_key must not be empty")
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
            if base_url is None:
                resolved_base_url = ClientConfig.resolve_base_url_from_env(
                    os.environ.get("HYPERBROWSER_BASE_URL")
                )
            else:
                resolved_base_url = base_url
            config = ClientConfig(
                api_key=resolved_api_key,
                base_url=resolved_base_url,
                headers=resolved_headers,
            )

        if not config.api_key:
            raise HyperbrowserError("API key must be provided")

        self.config = config
        self.transport = transport(config.api_key, headers=config.headers)

    @staticmethod
    def _parse_url_components(
        url_value: str, *, component_label: str
    ) -> tuple[str, str, str, str, str]:
        try:
            parsed_url = urlparse(url_value)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse {component_label}",
                original_error=exc,
            ) from exc
        try:
            parsed_url_scheme = parsed_url.scheme
            parsed_url_netloc = parsed_url.netloc
            parsed_url_path = parsed_url.path
            parsed_url_query = parsed_url.query
            parsed_url_fragment = parsed_url.fragment
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse {component_label} components",
                original_error=exc,
            ) from exc
        if (
            type(parsed_url_scheme) is not str
            or type(parsed_url_netloc) is not str
            or type(parsed_url_path) is not str
            or type(parsed_url_query) is not str
            or type(parsed_url_fragment) is not str
        ):
            raise HyperbrowserError(
                f"{component_label} parser returned invalid URL components"
            )
        return (
            parsed_url_scheme,
            parsed_url_netloc,
            parsed_url_path,
            parsed_url_query,
            parsed_url_fragment,
        )

    def _build_url(self, path: str) -> str:
        if not isinstance(path, str):
            raise HyperbrowserError("path must be a string")
        stripped_path = path.strip()
        if stripped_path != path:
            raise HyperbrowserError(
                "path must not contain leading or trailing whitespace"
            )
        if not stripped_path:
            raise HyperbrowserError("path must not be empty")
        if "\\" in stripped_path:
            raise HyperbrowserError("path must not contain backslashes")
        if "\n" in stripped_path or "\r" in stripped_path:
            raise HyperbrowserError("path must not contain newline characters")
        (
            parsed_path_scheme,
            _parsed_path_netloc,
            _parsed_path_path,
            parsed_path_query,
            parsed_path_fragment,
        ) = self._parse_url_components(stripped_path, component_label="path")
        if parsed_path_scheme:
            raise HyperbrowserError("path must be a relative API path")
        if parsed_path_fragment:
            raise HyperbrowserError("path must not include URL fragments")
        raw_query_component = (
            stripped_path.split("?", 1)[1] if "?" in stripped_path else ""
        )
        if "?" in raw_query_component or "#" in raw_query_component:
            raise HyperbrowserError(
                "path query must not contain unencoded delimiter characters"
            )
        if any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in raw_query_component
        ):
            raise HyperbrowserError(
                "path query must not contain unencoded whitespace or control characters"
            )
        if any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in parsed_path_query
        ):
            raise HyperbrowserError(
                "path query must not contain unencoded whitespace or control characters"
            )
        normalized_path = f"/{stripped_path.lstrip('/')}"
        (
            _normalized_path_scheme,
            _normalized_path_netloc,
            normalized_path_only,
            normalized_path_query,
            _normalized_path_fragment,
        ) = self._parse_url_components(normalized_path, component_label="normalized path")
        normalized_query_suffix = f"?{normalized_path_query}" if normalized_path_query else ""
        decoded_path = ClientConfig._decode_url_component_with_limit(
            normalized_path_only, component_label="path"
        )
        if "\\" in decoded_path:
            raise HyperbrowserError("path must not contain backslashes")
        if "\n" in decoded_path or "\r" in decoded_path:
            raise HyperbrowserError("path must not contain newline characters")
        if any(character.isspace() for character in decoded_path):
            raise HyperbrowserError("path must not contain whitespace characters")
        if any(
            ord(character) < 32 or ord(character) == 127 for character in decoded_path
        ):
            raise HyperbrowserError("path must not contain control characters")
        if "?" in decoded_path:
            raise HyperbrowserError("path must not contain encoded query delimiters")
        if "#" in decoded_path:
            raise HyperbrowserError("path must not contain encoded fragment delimiters")
        normalized_segments = [
            segment for segment in decoded_path.split("/") if segment
        ]
        if any(segment in {".", ".."} for segment in normalized_segments):
            raise HyperbrowserError("path must not contain relative path segments")
        normalized_base_url = ClientConfig.normalize_base_url(self.config.base_url)
        (
            _base_url_scheme,
            _base_url_netloc,
            parsed_base_url_path,
            _base_url_query,
            _base_url_fragment,
        ) = self._parse_url_components(normalized_base_url, component_label="base_url")
        base_has_api_suffix = parsed_base_url_path.rstrip("/").endswith("/api")

        if normalized_path_only == "/api" or normalized_path_only.startswith("/api/"):
            if base_has_api_suffix:
                deduped_path = normalized_path_only[len("/api") :]
                return f"{normalized_base_url}{deduped_path}{normalized_query_suffix}"
            return (
                f"{normalized_base_url}{normalized_path_only}{normalized_query_suffix}"
            )

        if base_has_api_suffix:
            return (
                f"{normalized_base_url}{normalized_path_only}{normalized_query_suffix}"
            )
        return (
            f"{normalized_base_url}/api{normalized_path_only}{normalized_query_suffix}"
        )
