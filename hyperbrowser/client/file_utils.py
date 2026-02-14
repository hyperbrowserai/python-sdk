import os
from os import PathLike
from typing import Union

from hyperbrowser.exceptions import HyperbrowserError


def _validate_error_message_text(message_value: str, *, field_name: str) -> None:
    if type(message_value) is not str:
        raise HyperbrowserError(f"{field_name} must be a string")
    try:
        normalized_message = message_value.strip()
        if type(normalized_message) is not str:
            raise TypeError(f"normalized {field_name} must be a string")
        is_empty = len(normalized_message) == 0
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to normalize {field_name}",
            original_error=exc,
        ) from exc
    if is_empty:
        raise HyperbrowserError(f"{field_name} must not be empty")
    try:
        contains_control_character = any(
            ord(character) < 32 or ord(character) == 127 for character in message_value
        )
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to validate {field_name} characters",
            original_error=exc,
        ) from exc
    if contains_control_character:
        raise HyperbrowserError(f"{field_name} must not contain control characters")


def ensure_existing_file_path(
    file_path: Union[str, PathLike[str]],
    *,
    missing_file_message: str,
    not_file_message: str,
) -> str:
    _validate_error_message_text(
        missing_file_message,
        field_name="missing_file_message",
    )
    _validate_error_message_text(
        not_file_message,
        field_name="not_file_message",
    )
    try:
        normalized_path = os.fspath(file_path)
    except HyperbrowserError:
        raise
    except TypeError as exc:
        raise HyperbrowserError(
            "file_path must be a string or os.PathLike object",
            original_error=exc,
        ) from exc
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if type(normalized_path) is not str:
        raise HyperbrowserError("file_path must resolve to a string path")
    try:
        stripped_normalized_path = normalized_path.strip()
        if type(stripped_normalized_path) is not str:
            raise TypeError("normalized file_path must be a string")
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if not stripped_normalized_path:
        raise HyperbrowserError("file_path must not be empty")
    try:
        has_surrounding_whitespace = normalized_path != stripped_normalized_path
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if has_surrounding_whitespace:
        raise HyperbrowserError(
            "file_path must not contain leading or trailing whitespace"
        )
    try:
        contains_null_byte = "\x00" in normalized_path
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if contains_null_byte:
        raise HyperbrowserError("file_path must not contain null bytes")
    try:
        contains_control_character = any(
            ord(character) < 32 or ord(character) == 127
            for character in normalized_path
        )
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if contains_control_character:
        raise HyperbrowserError("file_path must not contain control characters")
    try:
        path_exists = bool(os.path.exists(normalized_path))
    except HyperbrowserError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if not path_exists:
        raise HyperbrowserError(missing_file_message)
    try:
        is_file = bool(os.path.isfile(normalized_path))
    except HyperbrowserError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    except Exception as exc:
        raise HyperbrowserError("file_path is invalid", original_error=exc) from exc
    if not is_file:
        raise HyperbrowserError(not_file_message)
    return normalized_path
