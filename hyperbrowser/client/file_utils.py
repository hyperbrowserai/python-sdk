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
    normalized_path = os.fspath(file_path)
    if not os.path.exists(normalized_path):
        raise HyperbrowserError(missing_file_message)
    if not os.path.isfile(normalized_path):
        raise HyperbrowserError(not_file_message)
    return normalized_path
