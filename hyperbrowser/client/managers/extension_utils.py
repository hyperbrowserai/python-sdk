from collections.abc import Mapping
from typing import Any, List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import ExtensionResponse

_MAX_DISPLAYED_MISSING_KEYS = 20
_MAX_DISPLAYED_MISSING_KEY_LENGTH = 120


def _get_type_name(value: Any) -> str:
    return type(value).__name__


def _safe_stringify_key(value: object) -> str:
    try:
        return str(value)
    except Exception:
        return f"<unprintable {_get_type_name(value)}>"


def _format_key_display(value: object) -> str:
    normalized_key = _safe_stringify_key(value)
    if len(normalized_key) <= _MAX_DISPLAYED_MISSING_KEY_LENGTH:
        return normalized_key
    return (
        f"{normalized_key[:_MAX_DISPLAYED_MISSING_KEY_LENGTH]}"
        "... (truncated)"
    )


def _summarize_mapping_keys(mapping: Mapping[object, object]) -> str:
    try:
        mapping_keys = list(mapping.keys())
    except Exception:
        return "[<unavailable keys>]"
    key_names = sorted(_format_key_display(key) for key in mapping_keys)
    if not key_names:
        return "[]"
    displayed_keys = key_names[:_MAX_DISPLAYED_MISSING_KEYS]
    key_summary = ", ".join(displayed_keys)
    remaining_key_count = len(key_names) - len(displayed_keys)
    if remaining_key_count > 0:
        key_summary = f"{key_summary}, ... (+{remaining_key_count} more)"
    return f"[{key_summary}]"


def parse_extension_list_response_data(response_data: Any) -> List[ExtensionResponse]:
    if not isinstance(response_data, Mapping):
        raise HyperbrowserError(
            f"Expected mapping response but got {_get_type_name(response_data)}"
        )
    if "extensions" not in response_data:
        raise HyperbrowserError(
            "Expected 'extensions' key in response but got "
            f"{_summarize_mapping_keys(response_data)} keys"
        )
    try:
        extensions_value = response_data["extensions"]
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to read 'extensions' value from response",
            original_error=exc,
        ) from exc
    if not isinstance(extensions_value, list):
        raise HyperbrowserError(
            "Expected list in 'extensions' key but got "
            f"{_get_type_name(extensions_value)}"
        )
    parsed_extensions: List[ExtensionResponse] = []
    for index, extension in enumerate(extensions_value):
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
