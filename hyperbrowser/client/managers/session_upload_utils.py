import os
from os import PathLike
from typing import IO, Optional, Tuple, Union

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_string, is_string_subclass_instance

from ..file_utils import ensure_existing_file_path


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
        file_path = ensure_existing_file_path(
            raw_file_path,
            missing_file_message=f"Upload file not found at path: {raw_file_path}",
            not_file_message=f"Upload file path must point to a file: {raw_file_path}",
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
