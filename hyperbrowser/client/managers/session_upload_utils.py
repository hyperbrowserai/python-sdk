import os
from contextlib import contextmanager
from os import PathLike
from typing import Dict, IO, Iterator, Optional, Tuple, Union

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_string, is_string_subclass_instance

from ..file_utils import ensure_existing_file_path, open_binary_file

_MAX_FILE_PATH_DISPLAY_LENGTH = 200


def _format_upload_path_for_error(raw_file_path: object) -> str:
    if not is_plain_string(raw_file_path):
        return "<provided path>"
    try:
        normalized_path = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in raw_file_path
        )
    except Exception:
        return "<provided path>"
    if not is_plain_string(normalized_path):
        return "<provided path>"
    if len(normalized_path) <= _MAX_FILE_PATH_DISPLAY_LENGTH:
        return normalized_path
    return f"{normalized_path[:_MAX_FILE_PATH_DISPLAY_LENGTH]}..."


def normalize_upload_file_input(
    file_input: Union[str, PathLike[str], IO],
) -> Tuple[Optional[str], Optional[IO]]:
    if is_plain_string(file_input) or isinstance(file_input, PathLike):
        try:
            raw_file_path = os.fspath(file_input)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "file_input path is invalid",
                original_error=exc,
            ) from exc
        file_path_display = _format_upload_path_for_error(raw_file_path)
        file_path = ensure_existing_file_path(
            raw_file_path,
            missing_file_message=f"Upload file not found at path: {file_path_display}",
            not_file_message=f"Upload file path must point to a file: {file_path_display}",
        )
        return file_path, None

    if is_string_subclass_instance(file_input):
        raise HyperbrowserError("file_input path must be a plain string path")

    try:
        read_method = getattr(file_input, "read", None)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "file_input file-like object state is invalid",
            original_error=exc,
        ) from exc
    if not callable(read_method):
        raise HyperbrowserError("file_input must be a file path or file-like object")

    try:
        is_closed = bool(getattr(file_input, "closed", False))
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "file_input file-like object state is invalid",
            original_error=exc,
        ) from exc
    if is_closed:
        raise HyperbrowserError("file_input file-like object must be open")

    return None, file_input


@contextmanager
def open_upload_files_from_input(
    file_input: Union[str, PathLike[str], IO],
) -> Iterator[Dict[str, IO]]:
    file_path, file_obj = normalize_upload_file_input(file_input)
    if file_path is not None:
        with open_binary_file(
            file_path,
            open_error_message=f"Failed to open upload file at path: {file_path}",
        ) as opened_file:
            yield {"file": opened_file}
        return
    if file_obj is None:
        raise HyperbrowserError("file_input must be a file path or file-like object")
    yield {"file": file_obj}
