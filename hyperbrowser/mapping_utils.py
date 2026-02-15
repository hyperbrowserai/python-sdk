from collections.abc import Mapping as MappingABC
from typing import Any, Callable, Dict, List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_string


def safe_key_display_for_error(
    key: object, *, key_display: Callable[[object], object]
) -> str:
    try:
        key_text = key_display(key)
        if not is_plain_string(key_text):
            raise TypeError("mapping key display must be a string")
        if not key_text.strip():
            raise ValueError("mapping key display must not be blank")
        if any(ord(character) < 32 or ord(character) == 127 for character in key_text):
            raise ValueError("mapping key display must not contain control characters")
        return key_text
    except Exception:
        return "<unreadable key>"


def read_string_mapping_keys(
    mapping_value: Any,
    *,
    expected_mapping_error: str,
    read_keys_error: str,
    non_string_key_error_builder: Callable[[object], str],
) -> List[str]:
    if not isinstance(mapping_value, MappingABC):
        raise HyperbrowserError(expected_mapping_error)
    try:
        mapping_keys = list(mapping_value.keys())
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            read_keys_error,
            original_error=exc,
        ) from exc
    normalized_keys: List[str] = []
    for key in mapping_keys:
        if is_plain_string(key):
            normalized_keys.append(key)
            continue
        raise HyperbrowserError(non_string_key_error_builder(key))
    return normalized_keys


def read_string_key_mapping(
    mapping_value: Any,
    *,
    expected_mapping_error: str,
    read_keys_error: str,
    non_string_key_error_builder: Callable[[object], str],
    read_value_error_builder: Callable[[str], str],
    key_display: Callable[[object], object],
) -> Dict[str, object]:
    mapping_keys = read_string_mapping_keys(
        mapping_value,
        expected_mapping_error=expected_mapping_error,
        read_keys_error=read_keys_error,
        non_string_key_error_builder=non_string_key_error_builder,
    )
    normalized_mapping: Dict[str, object] = {}
    for key in mapping_keys:
        try:
            normalized_mapping[key] = mapping_value[key]
        except HyperbrowserError:
            raise
        except Exception as exc:
            key_text = safe_key_display_for_error(key, key_display=key_display)
            raise HyperbrowserError(
                read_value_error_builder(key_text),
                original_error=exc,
            ) from exc
    return normalized_mapping


def copy_mapping_values_by_string_keys(
    mapping_value: MappingABC[object, Any],
    keys: list[str],
    *,
    read_value_error_builder: Callable[[str], str],
    key_display: Callable[[object], object],
) -> Dict[str, object]:
    normalized_mapping: Dict[str, object] = {}
    for key in keys:
        if not is_plain_string(key):
            raise HyperbrowserError("mapping key list must contain plain strings")
        try:
            normalized_mapping[key] = mapping_value[key]
        except HyperbrowserError:
            raise
        except Exception as exc:
            key_text = safe_key_display_for_error(key, key_display=key_display)
            raise HyperbrowserError(
                read_value_error_builder(key_text),
                original_error=exc,
            ) from exc
    return normalized_mapping
