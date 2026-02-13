from collections.abc import Mapping
from typing import Any, List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import ExtensionResponse


def _get_type_name(value: Any) -> str:
    return type(value).__name__


def parse_extension_list_response_data(response_data: Any) -> List[ExtensionResponse]:
    if not isinstance(response_data, Mapping):
        raise HyperbrowserError(
            f"Expected mapping response but got {_get_type_name(response_data)}"
        )
    if "extensions" not in response_data:
        available_keys = ", ".join(sorted(str(key) for key in response_data.keys()))
        if available_keys:
            available_keys = f"[{available_keys}]"
        else:
            available_keys = "[]"
        raise HyperbrowserError(
            "Expected 'extensions' key in response but got "
            f"{available_keys} keys"
        )
    if not isinstance(response_data["extensions"], list):
        raise HyperbrowserError(
            "Expected list in 'extensions' key but got "
            f"{_get_type_name(response_data['extensions'])}"
        )
    parsed_extensions: List[ExtensionResponse] = []
    for index, extension in enumerate(response_data["extensions"]):
        if not isinstance(extension, Mapping):
            raise HyperbrowserError(
                "Expected extension object at index "
                f"{index} but got {_get_type_name(extension)}"
            )
        try:
            parsed_extensions.append(ExtensionResponse(**dict(extension)))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse extension at index {index}",
                original_error=exc,
            ) from exc
    return parsed_extensions
