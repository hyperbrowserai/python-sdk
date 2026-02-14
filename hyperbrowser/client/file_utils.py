import os
from contextlib import contextmanager
from os import PathLike
from typing import BinaryIO, Iterator, Optional, Union

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_int, is_plain_string

_MAX_FILE_PATH_DISPLAY_LENGTH = 200
_DEFAULT_OPEN_ERROR_MESSAGE_PREFIX = "Failed to open file at path"


def _sanitize_control_characters(value: str) -> str:
    return "".join(
        "?" if ord(character) < 32 or ord(character) == 127 else character
        for character in value
    )


def _normalize_error_prefix(prefix: object, *, default_prefix: str) -> str:
    normalized_default_prefix = default_prefix
    if not is_plain_string(normalized_default_prefix):
        normalized_default_prefix = _DEFAULT_OPEN_ERROR_MESSAGE_PREFIX
    else:
        try:
            sanitized_default_prefix = _sanitize_control_characters(
                normalized_default_prefix
            )
            stripped_default_prefix = sanitized_default_prefix.strip()
        except Exception:
            stripped_default_prefix = _DEFAULT_OPEN_ERROR_MESSAGE_PREFIX
        if not is_plain_string(stripped_default_prefix) or not stripped_default_prefix:
            normalized_default_prefix = _DEFAULT_OPEN_ERROR_MESSAGE_PREFIX
        else:
            normalized_default_prefix = stripped_default_prefix
    if not is_plain_string(prefix):
        return normalized_default_prefix
    try:
        sanitized_prefix = _sanitize_control_characters(prefix)
        stripped_prefix = sanitized_prefix.strip()
    except Exception:
        stripped_prefix = normalized_default_prefix
    if not is_plain_string(stripped_prefix) or not stripped_prefix:
        return normalized_default_prefix
    return stripped_prefix


def format_file_path_for_error(
    file_path: object,
    *,
    max_length: int = _MAX_FILE_PATH_DISPLAY_LENGTH,
) -> str:
    if not is_plain_int(max_length) or max_length <= 0:
        max_length = _MAX_FILE_PATH_DISPLAY_LENGTH
    try:
        path_value = (
            os.fspath(file_path)
            if is_plain_string(file_path) or isinstance(file_path, PathLike)
            else file_path
        )
    except Exception:
        return "<provided path>"
    if not is_plain_string(path_value):
        return "<provided path>"
    try:
        sanitized_path = _sanitize_control_characters(path_value)
    except Exception:
        return "<provided path>"
    if not is_plain_string(sanitized_path):
        return "<provided path>"
    if len(sanitized_path) <= max_length:
        return sanitized_path
    truncated_length = max_length - 3
    if truncated_length <= 0:
        return "..."
    return f"{sanitized_path[:truncated_length]}..."


def build_file_path_error_message(
    file_path: object,
    *,
    prefix: str,
    default_prefix: Optional[str] = None,
) -> str:
    normalized_prefix = _normalize_error_prefix(
        prefix,
        default_prefix=prefix if default_prefix is None else default_prefix,
    )
    file_path_display = format_file_path_for_error(file_path)
    return f"{normalized_prefix}: {file_path_display}"


def build_open_file_error_message(
    file_path: object,
    *,
    prefix: str,
    default_prefix: Optional[str] = None,
) -> str:
    return build_file_path_error_message(
        file_path,
        prefix=prefix,
        default_prefix=(
            _DEFAULT_OPEN_ERROR_MESSAGE_PREFIX
            if default_prefix is None
            else default_prefix
        ),
    )


def _normalize_file_path_text(file_path: Union[str, PathLike[str]]) -> str:
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
    if not is_plain_string(normalized_path):
        raise HyperbrowserError("file_path must resolve to a string path")
    try:
        stripped_normalized_path = normalized_path.strip()
        if not is_plain_string(stripped_normalized_path):
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
    return normalized_path


def _validate_error_message_text(message_value: str, *, field_name: str) -> None:
    if not is_plain_string(message_value):
        raise HyperbrowserError(f"{field_name} must be a string")
    try:
        normalized_message = message_value.strip()
        if not is_plain_string(normalized_message):
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
    normalized_path = _normalize_file_path_text(file_path)
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


@contextmanager
def open_binary_file(
    file_path: Union[str, PathLike[str]],
    *,
    open_error_message: str,
) -> Iterator[BinaryIO]:
    _validate_error_message_text(
        open_error_message,
        field_name="open_error_message",
    )
    normalized_path = _normalize_file_path_text(file_path)
    try:
        with open(normalized_path, "rb") as file_obj:
            yield file_obj
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            open_error_message,
            original_error=exc,
        ) from exc
