from collections.abc import Mapping
from typing import Any, Type, TypeVar

from hyperbrowser.exceptions import HyperbrowserError

T = TypeVar("T")
_MAX_OPERATION_NAME_DISPLAY_LENGTH = 120
_TRUNCATED_OPERATION_NAME_SUFFIX = "... (truncated)"


def _normalize_operation_name_for_error(operation_name: str) -> str:
    normalized_name = "".join(
        "?" if ord(character) < 32 or ord(character) == 127 else character
        for character in operation_name
    ).strip()
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


def parse_response_model(
    response_data: Any,
    *,
    model: Type[T],
    operation_name: str,
) -> T:
    if not isinstance(operation_name, str) or not operation_name.strip():
        raise HyperbrowserError("operation_name must be a non-empty string")
    normalized_operation_name = _normalize_operation_name_for_error(operation_name)
    if not isinstance(response_data, Mapping):
        raise HyperbrowserError(
            f"Expected {normalized_operation_name} response to be an object"
        )
    try:
        response_payload = dict(response_data)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to read {normalized_operation_name} response data",
            original_error=exc,
        ) from exc
    for key in response_payload.keys():
        if isinstance(key, str):
            continue
        raise HyperbrowserError(
            "Expected "
            f"{normalized_operation_name} response object keys to be strings"
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
