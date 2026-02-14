from typing import Any

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_string


def normalize_computer_action_endpoint(session: Any) -> str:
    try:
        computer_action_endpoint = session.computer_action_endpoint
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "session must include computer_action_endpoint",
            original_error=exc,
        ) from exc

    if computer_action_endpoint is None:
        raise HyperbrowserError("Computer action endpoint not available for this session")
    if not is_plain_string(computer_action_endpoint):
        raise HyperbrowserError("session computer_action_endpoint must be a string")
    try:
        normalized_computer_action_endpoint = computer_action_endpoint.strip()
        if not is_plain_string(normalized_computer_action_endpoint):
            raise TypeError("normalized computer_action_endpoint must be a string")
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to normalize session computer_action_endpoint",
            original_error=exc,
        ) from exc

    if not normalized_computer_action_endpoint:
        raise HyperbrowserError("Computer action endpoint not available for this session")
    if normalized_computer_action_endpoint != computer_action_endpoint:
        raise HyperbrowserError(
            "session computer_action_endpoint must not contain leading or trailing whitespace"
        )
    try:
        contains_control_character = any(
            ord(character) < 32 or ord(character) == 127
            for character in normalized_computer_action_endpoint
        )
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to validate session computer_action_endpoint characters",
            original_error=exc,
        ) from exc
    if contains_control_character:
        raise HyperbrowserError(
            "session computer_action_endpoint must not contain control characters"
        )
    return normalized_computer_action_endpoint
