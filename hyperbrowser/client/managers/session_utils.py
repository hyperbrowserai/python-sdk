from typing import Any, List, Type, TypeVar

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import SessionRecording
from .list_parsing_utils import parse_mapping_list_items
from .response_utils import parse_response_model

T = TypeVar("T")
_MAX_KEY_DISPLAY_LENGTH = 120
_TRUNCATED_KEY_DISPLAY_SUFFIX = "... (truncated)"


def _format_recording_key_display(key: str) -> str:
    try:
        normalized_key = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in key
        ).strip()
        if type(normalized_key) is not str:
            raise TypeError("normalized recording key display must be a string")
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
    if type(response_data) is not list:
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
    return parse_mapping_list_items(
        recording_items,
        item_label="session recording",
        parse_item=lambda recording_payload: SessionRecording(**recording_payload),
        key_display=_format_recording_key_display,
    )
