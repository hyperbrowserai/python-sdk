from typing import Any, List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import ExtensionResponse


def _get_type_name(value: Any) -> str:
    return type(value).__name__


def parse_extension_list_response_data(response_data: Any) -> List[ExtensionResponse]:
    if not isinstance(response_data, dict):
        raise HyperbrowserError(
            f"Expected dict response but got {_get_type_name(response_data)}"
        )
    if "extensions" not in response_data:
        raise HyperbrowserError(
            f"Expected 'extensions' key in response but got {response_data.keys()}"
        )
    if not isinstance(response_data["extensions"], list):
        raise HyperbrowserError(
            "Expected list in 'extensions' key but got "
            f"{_get_type_name(response_data['extensions'])}"
        )
    parsed_extensions: List[ExtensionResponse] = []
    for index, extension in enumerate(response_data["extensions"]):
        if not isinstance(extension, dict):
            raise HyperbrowserError(
                "Expected extension object at index "
                f"{index} but got {_get_type_name(extension)}"
            )
        try:
            parsed_extensions.append(ExtensionResponse(**extension))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse extension at index {index}",
                original_error=exc,
            ) from exc
    return parsed_extensions
