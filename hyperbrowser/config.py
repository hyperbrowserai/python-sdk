from dataclasses import dataclass
import re
from urllib.parse import unquote, urlparse
from typing import Dict, Mapping, Optional
import os

from .exceptions import HyperbrowserError
from .header_utils import normalize_headers, parse_headers_env_json

_ENCODED_HOST_DELIMITER_PATTERN = re.compile(r"%(?:2f|3f|23|40|3a)", re.IGNORECASE)


@dataclass
class ClientConfig:
    """Configuration for the Hyperbrowser client"""

    api_key: str
    base_url: str = "https://api.hyperbrowser.ai"
    headers: Optional[Mapping[str, str]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str):
            raise HyperbrowserError("api_key must be a string")
        self.api_key = self.api_key.strip()
        if not self.api_key:
            raise HyperbrowserError("api_key must not be empty")
        if any(
            ord(character) < 32 or ord(character) == 127 for character in self.api_key
        ):
            raise HyperbrowserError("api_key must not contain control characters")
        self.base_url = self.normalize_base_url(self.base_url)
        self.headers = normalize_headers(
            self.headers,
            mapping_error_message="headers must be a mapping of string pairs",
        )

    @staticmethod
    def _decode_url_component_with_limit(value: str, *, component_label: str) -> str:
        decoded_value = value
        for _ in range(10):
            next_decoded_value = ClientConfig._safe_unquote(
                decoded_value,
                component_label=component_label,
            )
            if next_decoded_value == decoded_value:
                return decoded_value
            decoded_value = next_decoded_value
        if (
            ClientConfig._safe_unquote(
                decoded_value,
                component_label=component_label,
            )
            == decoded_value
        ):
            return decoded_value
        raise HyperbrowserError(
            f"{component_label} contains excessively nested URL encoding"
        )

    @staticmethod
    def _safe_unquote(value: str, *, component_label: str) -> str:
        try:
            decoded_value = unquote(value)
            if not isinstance(decoded_value, str):
                raise TypeError("decoded URL component must be a string")
            return decoded_value
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to decode {component_label}",
                original_error=exc,
            ) from exc

    @staticmethod
    def normalize_base_url(base_url: str) -> str:
        if not isinstance(base_url, str):
            raise HyperbrowserError("base_url must be a string")
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise HyperbrowserError("base_url must not be empty")
        if "\n" in normalized_base_url or "\r" in normalized_base_url:
            raise HyperbrowserError("base_url must not contain newline characters")
        if any(character.isspace() for character in normalized_base_url):
            raise HyperbrowserError("base_url must not contain whitespace characters")
        if "\\" in normalized_base_url:
            raise HyperbrowserError("base_url must not contain backslashes")
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in normalized_base_url
        ):
            raise HyperbrowserError("base_url must not contain control characters")

        try:
            parsed_base_url = urlparse(normalized_base_url)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to parse base_url",
                original_error=exc,
            ) from exc
        if (
            not isinstance(parsed_base_url.scheme, str)
            or not isinstance(parsed_base_url.netloc, str)
            or not isinstance(parsed_base_url.path, str)
            or not isinstance(parsed_base_url.query, str)
            or not isinstance(parsed_base_url.fragment, str)
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        if (
            parsed_base_url.hostname is not None
            and not isinstance(parsed_base_url.hostname, str)
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        if (
            parsed_base_url.scheme not in {"https", "http"}
            or not parsed_base_url.netloc
        ):
            raise HyperbrowserError(
                "base_url must start with 'https://' or 'http://' and include a host"
            )
        if parsed_base_url.hostname is None:
            raise HyperbrowserError(
                "base_url must start with 'https://' or 'http://' and include a host"
            )
        if parsed_base_url.query or parsed_base_url.fragment:
            raise HyperbrowserError(
                "base_url must not include query parameters or fragments"
            )
        if parsed_base_url.username is not None or parsed_base_url.password is not None:
            raise HyperbrowserError("base_url must not include user credentials")
        try:
            parsed_base_url.port
        except HyperbrowserError:
            raise
        except ValueError as exc:
            raise HyperbrowserError(
                "base_url must contain a valid port number",
                original_error=exc,
            ) from exc
        except Exception as exc:
            raise HyperbrowserError(
                "base_url must contain a valid port number",
                original_error=exc,
            ) from exc

        decoded_base_path = ClientConfig._decode_url_component_with_limit(
            parsed_base_url.path, component_label="base_url path"
        )
        if "\\" in decoded_base_path:
            raise HyperbrowserError("base_url must not contain backslashes")
        if any(character.isspace() for character in decoded_base_path):
            raise HyperbrowserError("base_url must not contain whitespace characters")
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in decoded_base_path
        ):
            raise HyperbrowserError("base_url must not contain control characters")
        path_segments = [segment for segment in decoded_base_path.split("/") if segment]
        if any(segment in {".", ".."} for segment in path_segments):
            raise HyperbrowserError(
                "base_url path must not contain relative path segments"
            )
        if "?" in decoded_base_path or "#" in decoded_base_path:
            raise HyperbrowserError(
                "base_url path must not contain encoded query or fragment delimiters"
            )

        decoded_base_netloc = parsed_base_url.netloc
        for _ in range(10):
            if _ENCODED_HOST_DELIMITER_PATTERN.search(decoded_base_netloc):
                raise HyperbrowserError(
                    "base_url host must not contain encoded delimiter characters"
                )
            next_decoded_base_netloc = ClientConfig._safe_unquote(
                decoded_base_netloc,
                component_label="base_url host",
            )
            if next_decoded_base_netloc == decoded_base_netloc:
                break
            decoded_base_netloc = next_decoded_base_netloc
        else:
            if _ENCODED_HOST_DELIMITER_PATTERN.search(decoded_base_netloc):
                raise HyperbrowserError(
                    "base_url host must not contain encoded delimiter characters"
                )
            if (
                ClientConfig._safe_unquote(
                    decoded_base_netloc,
                    component_label="base_url host",
                )
                != decoded_base_netloc
            ):
                raise HyperbrowserError(
                    "base_url host contains excessively nested URL encoding"
                )
        if "\\" in decoded_base_netloc:
            raise HyperbrowserError("base_url host must not contain backslashes")
        if any(character.isspace() for character in decoded_base_netloc):
            raise HyperbrowserError(
                "base_url host must not contain whitespace characters"
            )
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in decoded_base_netloc
        ):
            raise HyperbrowserError("base_url host must not contain control characters")
        if any(character in {"?", "#", "/", "@"} for character in decoded_base_netloc):
            raise HyperbrowserError(
                "base_url host must not contain encoded delimiter characters"
            )
        return normalized_base_url

    @classmethod
    def from_env(cls) -> "ClientConfig":
        api_key = os.environ.get("HYPERBROWSER_API_KEY")
        if api_key is None or not api_key.strip():
            raise HyperbrowserError(
                "HYPERBROWSER_API_KEY environment variable is required"
            )

        base_url = cls.resolve_base_url_from_env(
            os.environ.get("HYPERBROWSER_BASE_URL")
        )
        headers = cls.parse_headers_from_env(os.environ.get("HYPERBROWSER_HEADERS"))
        return cls(api_key=api_key, base_url=base_url, headers=headers)

    @staticmethod
    def parse_headers_from_env(raw_headers: Optional[str]) -> Optional[Dict[str, str]]:
        return parse_headers_env_json(raw_headers)

    @staticmethod
    def resolve_base_url_from_env(raw_base_url: Optional[str]) -> str:
        if raw_base_url is None:
            return "https://api.hyperbrowser.ai"
        if not isinstance(raw_base_url, str):
            raise HyperbrowserError("HYPERBROWSER_BASE_URL must be a string")
        if not raw_base_url.strip():
            raise HyperbrowserError("HYPERBROWSER_BASE_URL must not be empty when set")
        return ClientConfig.normalize_base_url(raw_base_url)
