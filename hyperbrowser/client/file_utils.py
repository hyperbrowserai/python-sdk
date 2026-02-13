import os
from os import PathLike
from typing import Union

from hyperbrowser.exceptions import HyperbrowserError


def ensure_existing_file_path(
    file_path: Union[str, PathLike[str]],
    *,
    missing_file_message: str,
    not_file_message: str,
) -> str:
    if not isinstance(missing_file_message, str):
        raise HyperbrowserError("missing_file_message must be a string")
    if not missing_file_message.strip():
        raise HyperbrowserError("missing_file_message must not be empty")
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in missing_file_message
    ):
        raise HyperbrowserError(
            "missing_file_message must not contain control characters"
        )
    if not isinstance(not_file_message, str):
        raise HyperbrowserError("not_file_message must be a string")
    if not not_file_message.strip():
        raise HyperbrowserError("not_file_message must not be empty")
    if any(
        ord(character) < 32 or ord(character) == 127 for character in not_file_message
    ):
        raise HyperbrowserError("not_file_message must not contain control characters")
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
    if not isinstance(normalized_path, str):
        raise HyperbrowserError("file_path must resolve to a string path")
    if not normalized_path.strip():
        raise HyperbrowserError("file_path must not be empty")
    if normalized_path != normalized_path.strip():
        raise HyperbrowserError(
            "file_path must not contain leading or trailing whitespace"
        )
    if "\x00" in normalized_path:
        raise HyperbrowserError("file_path must not contain null bytes")
    if any(
        ord(character) < 32 or ord(character) == 127 for character in normalized_path
    ):
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
