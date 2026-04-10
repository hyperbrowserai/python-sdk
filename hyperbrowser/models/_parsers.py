from typing import Any


def _parse_optional_int(value: Any):
    if value is None or isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, str):
        return int(value)
    return value
