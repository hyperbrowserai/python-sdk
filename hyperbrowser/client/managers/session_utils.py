from typing import Any, List, Type, TypeVar

from hyperbrowser.display_utils import format_string_key_for_error
from hyperbrowser.models.session import SessionRecording
from .list_parsing_utils import parse_mapping_list_items, read_plain_list_items
from .response_utils import parse_response_model

T = TypeVar("T")
_MAX_KEY_DISPLAY_LENGTH = 120


def _format_recording_key_display(key: str) -> str:
    return format_string_key_for_error(key, max_length=_MAX_KEY_DISPLAY_LENGTH)


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
    recording_items = read_plain_list_items(
        response_data,
        expected_list_error="Expected session recording response to be a list of objects",
        read_list_error="Failed to iterate session recording response list",
    )
    return parse_mapping_list_items(
        recording_items,
        item_label="session recording",
        parse_item=lambda recording_payload: SessionRecording(**recording_payload),
        key_display=_format_recording_key_display,
    )
