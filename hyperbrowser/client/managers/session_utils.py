from collections.abc import Mapping
from typing import Any, List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import SessionRecording


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
