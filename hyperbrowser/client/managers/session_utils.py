from collections.abc import Mapping
from typing import Any, List, Type, TypeVar

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import SessionRecording
from .response_utils import parse_response_model

T = TypeVar("T")
_MAX_KEY_DISPLAY_LENGTH = 120
_TRUNCATED_KEY_DISPLAY_SUFFIX = "... (truncated)"


def _format_recording_key_display(key: str) -> str:
    normalized_key = "".join(
        "?" if ord(character) < 32 or ord(character) == 127 else character
        for character in key
    ).strip()
    if not normalized_key:
        return "<blank key>"
    if len(normalized_key) <= _MAX_KEY_DISPLAY_LENGTH:
        return normalized_key
    available_length = _MAX_KEY_DISPLAY_LENGTH - len(_TRUNCATED_KEY_DISPLAY_SUFFIX)
    if available_length <= 0:
        return _TRUNCATED_KEY_DISPLAY_SUFFIX
    return f"{normalized_key[:available_length]}{_TRUNCATED_KEY_DISPLAY_SUFFIX}"


def parse_session_response_model(
    response_data: Any,
    *,
    model: Type[T],
    operation_name: str,
) -> T:
    return parse_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


def parse_session_recordings_response_data(
    response_data: Any,
) -> List[SessionRecording]:
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
            recording_keys = list(recording.keys())
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read session recording object at index {index}",
                original_error=exc,
            ) from exc
        for key in recording_keys:
            if isinstance(key, str):
                continue
            raise HyperbrowserError(
                f"Expected session recording object keys to be strings at index {index}"
            )
        recording_payload: dict[str, object] = {}
        for key in recording_keys:
            try:
                recording_payload[key] = recording[key]
            except HyperbrowserError:
                raise
            except Exception as exc:
                key_display = _format_recording_key_display(key)
                raise HyperbrowserError(
                    "Failed to read session recording object value for key "
                    f"'{key_display}' at index {index}",
                    original_error=exc,
                ) from exc
        try:
            parsed_recordings.append(SessionRecording(**recording_payload))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse session recording at index {index}",
                original_error=exc,
            ) from exc
    return parsed_recordings
