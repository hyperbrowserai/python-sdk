from collections.abc import Mapping as MappingABC
from abc import ABC, abstractmethod
from typing import Generic, Mapping, Optional, Type, TypeVar, Union

from hyperbrowser.exceptions import HyperbrowserError

T = TypeVar("T")
_TRUNCATED_DISPLAY_SUFFIX = "... (truncated)"
_MAX_MODEL_NAME_DISPLAY_LENGTH = 120
_MAX_MAPPING_KEY_DISPLAY_LENGTH = 120
_MIN_HTTP_STATUS_CODE = 100
_MAX_HTTP_STATUS_CODE = 599


def _sanitize_display_text(value: str, *, max_length: int) -> str:
    sanitized_value = "".join(
        "?" if ord(character) < 32 or ord(character) == 127 else character
        for character in value
    ).strip()
    if not sanitized_value:
        return ""
    if len(sanitized_value) <= max_length:
        return sanitized_value
    available_length = max_length - len(_TRUNCATED_DISPLAY_SUFFIX)
    if available_length <= 0:
        return _TRUNCATED_DISPLAY_SUFFIX
    return f"{sanitized_value[:available_length]}{_TRUNCATED_DISPLAY_SUFFIX}"


def _safe_model_name(model: object) -> str:
    try:
        model_name = getattr(model, "__name__", "response model")
    except Exception:
        return "response model"
    if not isinstance(model_name, str):
        return "response model"
    normalized_model_name = _sanitize_display_text(
        model_name, max_length=_MAX_MODEL_NAME_DISPLAY_LENGTH
    )
    if not normalized_model_name:
        return "response model"
    return normalized_model_name


def _format_mapping_key_for_error(key: str) -> str:
    normalized_key = _sanitize_display_text(
        key, max_length=_MAX_MAPPING_KEY_DISPLAY_LENGTH
    )
    if normalized_key:
        return normalized_key
    return "<blank key>"


def _normalize_transport_api_key(api_key: str) -> str:
    if not isinstance(api_key, str):
        raise HyperbrowserError("api_key must be a string")

    try:
        normalized_api_key = api_key.strip()
        if not isinstance(normalized_api_key, str):
            raise TypeError("normalized api_key must be a string")
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to normalize api_key",
            original_error=exc,
        ) from exc

    if not normalized_api_key:
        raise HyperbrowserError("api_key must not be empty")

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


class APIResponse(Generic[T]):
    """
    Wrapper for API responses to standardize sync/async handling.
    """

    def __init__(self, data: Optional[Union[dict, T]] = None, status_code: int = 200):
        if isinstance(status_code, bool) or not isinstance(status_code, int):
            raise HyperbrowserError("status_code must be an integer")
        if not (_MIN_HTTP_STATUS_CODE <= status_code <= _MAX_HTTP_STATUS_CODE):
            raise HyperbrowserError("status_code must be between 100 and 599")
        self.data = data
        self.status_code = status_code

    @classmethod
    def from_json(
        cls, json_data: Mapping[str, object], model: Type[T]
    ) -> "APIResponse[T]":
        """Create an APIResponse from JSON data with a specific model."""
        model_name = _safe_model_name(model)
        if not isinstance(json_data, MappingABC):
            actual_type_name = type(json_data).__name__
            raise HyperbrowserError(
                f"Failed to parse response data for {model_name}: "
                f"expected a mapping but received {actual_type_name}"
            )
        try:
            response_keys = list(json_data.keys())
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse response data for {model_name}: "
                "unable to read mapping keys",
                original_error=exc,
            ) from exc
        for key in response_keys:
            if isinstance(key, str):
                continue
            key_type_name = type(key).__name__
            raise HyperbrowserError(
                f"Failed to parse response data for {model_name}: "
                f"expected string keys but received {key_type_name}"
            )
        normalized_payload: dict[str, object] = {}
        for key in response_keys:
            try:
                normalized_payload[key] = json_data[key]
            except HyperbrowserError:
                raise
            except Exception as exc:
                key_display = _format_mapping_key_for_error(key)
                raise HyperbrowserError(
                    f"Failed to parse response data for {model_name}: "
                    f"unable to read value for key '{key_display}'",
                    original_error=exc,
                ) from exc
        try:
            return cls(data=model(**normalized_payload))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse response data for {model_name}",
                original_error=exc,
            ) from exc

    @classmethod
    def from_status(cls, status_code: int) -> "APIResponse[None]":
        """Create an APIResponse from just a status code."""
        return cls(data=None, status_code=status_code)

    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return 200 <= self.status_code < 300


class SyncTransportStrategy(ABC):
    """Abstract base class for synchronous transport implementations"""

    @abstractmethod
    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None): ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def post(
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse: ...

    @abstractmethod
    def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse: ...

    @abstractmethod
    def put(self, url: str, data: Optional[dict] = None) -> APIResponse: ...

    @abstractmethod
    def delete(self, url: str) -> APIResponse: ...


class AsyncTransportStrategy(ABC):
    """Abstract base class for asynchronous transport implementations"""

    @abstractmethod
    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None): ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def post(
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse: ...

    @abstractmethod
    async def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse: ...

    @abstractmethod
    async def put(self, url: str, data: Optional[dict] = None) -> APIResponse: ...

    @abstractmethod
    async def delete(self, url: str) -> APIResponse: ...


class TransportStrategy(SyncTransportStrategy):
    """Backward-compatible alias for the sync transport interface."""
