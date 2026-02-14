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
        self.api_key = self.normalize_api_key(self.api_key)
        self.base_url = self.normalize_base_url(self.base_url)
        self.headers = normalize_headers(
            self.headers,
            mapping_error_message="headers must be a mapping of string pairs",
        )

    @staticmethod
    def normalize_api_key(
        api_key: str,
        *,
        empty_error_message: str = "api_key must not be empty",
    ) -> str:
        if not isinstance(api_key, str):
            raise HyperbrowserError("api_key must be a string")
        try:
            normalized_api_key = api_key.strip()
            if type(normalized_api_key) is not str:
                raise TypeError("normalized api_key must be a string")
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize api_key",
                original_error=exc,
            ) from exc
        try:
            is_empty_api_key = len(normalized_api_key) == 0
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize api_key",
                original_error=exc,
            ) from exc
        if is_empty_api_key:
            raise HyperbrowserError(empty_error_message)
        try:
            contains_control_character = any(
                ord(character) < 32 or ord(character) == 127
                for character in normalized_api_key
            )
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to validate api_key characters",
                original_error=exc,
            ) from exc
        if contains_control_character:
            raise HyperbrowserError("api_key must not contain control characters")
        return normalized_api_key

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
            if type(decoded_value) is not str:
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
        try:
            stripped_base_url = base_url.strip()
            if type(stripped_base_url) is not str:
                raise TypeError("normalized base_url must be a string")
            normalized_base_url = stripped_base_url.rstrip("/")
            if type(normalized_base_url) is not str:
                raise TypeError("normalized base_url must be a string")
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize base_url",
                original_error=exc,
            ) from exc
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
        try:
            parsed_base_url_scheme = parsed_base_url.scheme
            parsed_base_url_netloc = parsed_base_url.netloc
            parsed_base_url_path = parsed_base_url.path
            parsed_base_url_query = parsed_base_url.query
            parsed_base_url_fragment = parsed_base_url.fragment
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to parse base_url components",
                original_error=exc,
            ) from exc
        if (
            type(parsed_base_url_scheme) is not str
            or type(parsed_base_url_netloc) is not str
            or type(parsed_base_url_path) is not str
            or type(parsed_base_url_query) is not str
            or type(parsed_base_url_fragment) is not str
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        try:
            parsed_base_url_hostname = parsed_base_url.hostname
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to parse base_url host",
                original_error=exc,
            ) from exc
        if (
            parsed_base_url_hostname is not None
            and type(parsed_base_url_hostname) is not str
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        if (
            parsed_base_url_scheme not in {"https", "http"}
            or not parsed_base_url_netloc
        ):
            raise HyperbrowserError(
                "base_url must start with 'https://' or 'http://' and include a host"
            )
        if parsed_base_url_hostname is None:
            raise HyperbrowserError(
                "base_url must start with 'https://' or 'http://' and include a host"
            )
        if parsed_base_url_query or parsed_base_url_fragment:
            raise HyperbrowserError(
                "base_url must not include query parameters or fragments"
            )
        try:
            parsed_base_url_username = parsed_base_url.username
            parsed_base_url_password = parsed_base_url.password
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to parse base_url credentials",
                original_error=exc,
            ) from exc
        if (
            parsed_base_url_username is not None
            and type(parsed_base_url_username) is not str
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        if (
            parsed_base_url_password is not None
            and type(parsed_base_url_password) is not str
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        if parsed_base_url_username is not None or parsed_base_url_password is not None:
            raise HyperbrowserError("base_url must not include user credentials")
        try:
            parsed_base_url_port = parsed_base_url.port
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
        if parsed_base_url_port is not None and (
            isinstance(parsed_base_url_port, bool)
            or not isinstance(parsed_base_url_port, int)
        ):
            raise HyperbrowserError("base_url parser returned invalid URL components")
        if parsed_base_url_port is not None and not (0 <= parsed_base_url_port <= 65535):
            raise HyperbrowserError("base_url parser returned invalid URL components")

        decoded_base_path = ClientConfig._decode_url_component_with_limit(
            parsed_base_url_path, component_label="base_url path"
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

        decoded_base_netloc = parsed_base_url_netloc
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
        api_key = cls._read_env_value("HYPERBROWSER_API_KEY")
        if api_key is None:
            raise HyperbrowserError(
                "HYPERBROWSER_API_KEY environment variable is required"
            )
        api_key = cls.normalize_api_key(
            api_key,
            empty_error_message="HYPERBROWSER_API_KEY environment variable is required",
        )

        base_url = cls.resolve_base_url_from_env(
            cls._read_env_value("HYPERBROWSER_BASE_URL")
        )
        headers = cls.parse_headers_from_env(cls._read_env_value("HYPERBROWSER_HEADERS"))
        return cls(api_key=api_key, base_url=base_url, headers=headers)

    @staticmethod
    def _read_env_value(env_name: str) -> Optional[str]:
        try:
            return os.environ.get(env_name)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {env_name} environment variable",
                original_error=exc,
            ) from exc

    @staticmethod
    def parse_headers_from_env(raw_headers: Optional[str]) -> Optional[Dict[str, str]]:
        return parse_headers_env_json(raw_headers)

    @staticmethod
    def resolve_base_url_from_env(raw_base_url: Optional[str]) -> str:
        if raw_base_url is None:
            return "https://api.hyperbrowser.ai"
        if type(raw_base_url) is not str:
            raise HyperbrowserError("HYPERBROWSER_BASE_URL must be a string")
        try:
            normalized_env_base_url = raw_base_url.strip()
            if type(normalized_env_base_url) is not str:
                raise TypeError("normalized environment base_url must be a string")
            is_empty_env_base_url = len(normalized_env_base_url) == 0
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize HYPERBROWSER_BASE_URL",
                original_error=exc,
            ) from exc
        if is_empty_env_base_url:
            raise HyperbrowserError("HYPERBROWSER_BASE_URL must not be empty when set")
        return ClientConfig.normalize_base_url(normalized_env_base_url)
