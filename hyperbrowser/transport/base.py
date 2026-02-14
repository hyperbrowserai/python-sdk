from abc import ABC, abstractmethod
from typing import Generic, Mapping, Optional, Type, TypeVar, Union

from hyperbrowser.display_utils import (
    format_string_key_for_error,
    normalize_display_text,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.mapping_utils import read_string_key_mapping

T = TypeVar("T")
_MAX_MODEL_NAME_DISPLAY_LENGTH = 120
_MAX_MAPPING_KEY_DISPLAY_LENGTH = 120
_MIN_HTTP_STATUS_CODE = 100
_MAX_HTTP_STATUS_CODE = 599


def _safe_model_name(model: object) -> str:
    try:
        model_name = getattr(model, "__name__", "response model")
    except Exception:
        return "response model"
    if type(model_name) is not str:
        return "response model"
    try:
        normalized_model_name = normalize_display_text(
            model_name, max_length=_MAX_MODEL_NAME_DISPLAY_LENGTH
        )
    except Exception:
        return "response model"
    if not normalized_model_name:
        return "response model"
    return normalized_model_name


def _format_mapping_key_for_error(key: str) -> str:
    return format_string_key_for_error(
        key,
        max_length=_MAX_MAPPING_KEY_DISPLAY_LENGTH,
    )


def _normalize_transport_api_key(api_key: str) -> str:
    if type(api_key) is not str:
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
        if type(status_code) is not int:
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
        normalized_payload = read_string_key_mapping(
            json_data,
            expected_mapping_error=(
                f"Failed to parse response data for {model_name}: expected a mapping "
                f"but received {type(json_data).__name__}"
            ),
            read_keys_error=(
                f"Failed to parse response data for {model_name}: "
                "unable to read mapping keys"
            ),
            non_string_key_error_builder=lambda key: (
                f"Failed to parse response data for {model_name}: "
                f"expected string keys but received {type(key).__name__}"
            ),
            read_value_error_builder=lambda key_display: (
                f"Failed to parse response data for {model_name}: "
                f"unable to read value for key '{key_display}'"
            ),
            key_display=_format_mapping_key_for_error,
        )
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
