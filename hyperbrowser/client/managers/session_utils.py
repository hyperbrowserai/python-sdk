from collections.abc import Mapping
from typing import Any, List, Type, TypeVar

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import SessionRecording

T = TypeVar("T")


def parse_session_response_model(
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


def parse_session_recordings_response_data(response_data: Any) -> List[SessionRecording]:
    if not isinstance(response_data, list):
        raise HyperbrowserError(
            "Expected session recording response to be a list of objects"
        )
    try:
        recording_items = list(response_data)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to iterate session recording response list",
            original_error=exc,
        ) from exc
    parsed_recordings: List[SessionRecording] = []
    for index, recording in enumerate(recording_items):
        if not isinstance(recording, Mapping):
            raise HyperbrowserError(
                "Expected session recording object at index "
                f"{index} but got {type(recording).__name__}"
            )
        try:
            parsed_recordings.append(SessionRecording(**dict(recording)))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse session recording at index {index}",
                original_error=exc,
            ) from exc
    return parsed_recordings
