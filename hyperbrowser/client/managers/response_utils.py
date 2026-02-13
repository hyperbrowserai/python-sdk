from collections.abc import Mapping
from typing import Any, Type, TypeVar

from hyperbrowser.exceptions import HyperbrowserError

T = TypeVar("T")


def parse_response_model(
    response_data: Any,
    *,
    model: Type[T],
    operation_name: str,
) -> T:
    if not isinstance(operation_name, str) or not operation_name.strip():
        raise HyperbrowserError("operation_name must be a non-empty string")
    if not isinstance(response_data, Mapping):
        raise HyperbrowserError(f"Expected {operation_name} response to be an object")
    try:
        response_payload = dict(response_data)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to read {operation_name} response data",
            original_error=exc,
        ) from exc
    try:
        return model(**response_payload)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to parse {operation_name} response",
            original_error=exc,
        ) from exc
