from collections.abc import Mapping
from typing import Any, List

from hyperbrowser.display_utils import format_string_key_for_error
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import ExtensionResponse
from hyperbrowser.type_utils import is_plain_string
from .list_parsing_utils import parse_mapping_list_items, read_plain_list_items

_MAX_DISPLAYED_MISSING_KEYS = 20
_MAX_DISPLAYED_MISSING_KEY_LENGTH = 120


def _get_type_name(value: Any) -> str:
    return type(value).__name__


def _safe_stringify_key(value: object) -> str:
    try:
        normalized_key = str(value)
        if not is_plain_string(normalized_key):
            raise TypeError("normalized key must be a string")
        return normalized_key
    except Exception:
        return f"<unprintable {_get_type_name(value)}>"


def _format_key_display(value: object) -> str:
    try:
        normalized_key = _safe_stringify_key(value)
        if not is_plain_string(normalized_key):
            raise TypeError("normalized key display must be a string")
    except Exception:
        return "<unreadable key>"
    return format_string_key_for_error(
        normalized_key,
        max_length=_MAX_DISPLAYED_MISSING_KEY_LENGTH,
    )


def _summarize_mapping_keys(mapping: Mapping[object, object]) -> str:
    try:
        mapping_keys = list(mapping.keys())
    except HyperbrowserError:
        raise
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
    try:
        has_extensions_key = "extensions" in response_data
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to inspect response for 'extensions' key",
            original_error=exc,
        ) from exc
    if not has_extensions_key:
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
    extension_items = read_plain_list_items(
        extensions_value,
        expected_list_error=(
            "Expected list in 'extensions' key but got "
            f"{_get_type_name(extensions_value)}"
        ),
        read_list_error="Failed to iterate 'extensions' list from response",
    )
    return parse_mapping_list_items(
        extension_items,
        item_label="extension",
        parse_item=lambda extension_payload: ExtensionResponse(**extension_payload),
        key_display=_format_key_display,
    )
