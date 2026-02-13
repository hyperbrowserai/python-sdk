import os

from hyperbrowser.exceptions import HyperbrowserError


def ensure_existing_file_path(
    file_path: str,
    *,
    missing_file_message: str,
    not_file_message: str,
) -> None:
    if not os.path.exists(file_path):
        raise HyperbrowserError(missing_file_message)
    if not os.path.isfile(file_path):
        raise HyperbrowserError(not_file_message)
