from typing import Any, Type, TypeVar

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.mapping_utils import read_string_key_mapping

T = TypeVar("T")
_MAX_OPERATION_NAME_DISPLAY_LENGTH = 120
_TRUNCATED_OPERATION_NAME_SUFFIX = "... (truncated)"
_MAX_KEY_DISPLAY_LENGTH = 120
_TRUNCATED_KEY_DISPLAY_SUFFIX = "... (truncated)"


def _normalize_operation_name_for_error(operation_name: str) -> str:
    try:
        normalized_name = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in operation_name
        ).strip()
        if type(normalized_name) is not str:
            raise TypeError("normalized operation name must be a string")
    except Exception:
        return "operation"
    if not normalized_name:
        return "operation"
    if len(normalized_name) <= _MAX_OPERATION_NAME_DISPLAY_LENGTH:
        return normalized_name
    available_length = _MAX_OPERATION_NAME_DISPLAY_LENGTH - len(
        _TRUNCATED_OPERATION_NAME_SUFFIX
    )
    if available_length <= 0:
        return _TRUNCATED_OPERATION_NAME_SUFFIX
    return f"{normalized_name[:available_length]}{_TRUNCATED_OPERATION_NAME_SUFFIX}"


def _normalize_response_key_for_error(key: str) -> str:
    try:
        normalized_key = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in key
        ).strip()
        if type(normalized_key) is not str:
            raise TypeError("normalized response key must be a string")
    except Exception:
        return "<unreadable key>"
    if not normalized_key:
        return "<blank key>"
    if len(normalized_key) <= _MAX_KEY_DISPLAY_LENGTH:
        return normalized_key
    available_length = _MAX_KEY_DISPLAY_LENGTH - len(_TRUNCATED_KEY_DISPLAY_SUFFIX)
    if available_length <= 0:
        return _TRUNCATED_KEY_DISPLAY_SUFFIX
    return f"{normalized_key[:available_length]}{_TRUNCATED_KEY_DISPLAY_SUFFIX}"


def parse_response_model(
    response_data: Any,
    *,
    model: Type[T],
    operation_name: str,
) -> T:
    if type(operation_name) is not str:
        raise HyperbrowserError("operation_name must be a non-empty string")
    try:
        normalized_operation_name_input = operation_name.strip()
        if type(normalized_operation_name_input) is not str:
            raise TypeError("normalized operation_name must be a string")
        is_empty_operation_name = len(normalized_operation_name_input) == 0
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to normalize operation_name",
            original_error=exc,
        ) from exc
    if is_empty_operation_name:
        raise HyperbrowserError("operation_name must be a non-empty string")
    normalized_operation_name = _normalize_operation_name_for_error(operation_name)
    response_payload = read_string_key_mapping(
        response_data,
        expected_mapping_error=(
            f"Expected {normalized_operation_name} response to be an object"
        ),
        read_keys_error=f"Failed to read {normalized_operation_name} response keys",
        non_string_key_error_builder=lambda _key: (
            f"Expected {normalized_operation_name} response object keys to be strings"
        ),
        read_value_error_builder=lambda key_display: (
            f"Failed to read {normalized_operation_name} response value for key "
            f"'{key_display}'"
        ),
        key_display=_normalize_response_key_for_error,
    )
    try:
        return model(**response_payload)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to parse {normalized_operation_name} response",
            original_error=exc,
        ) from exc
