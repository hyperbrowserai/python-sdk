from collections.abc import Mapping as MappingABC
from typing import Any, Callable, Dict, List

from hyperbrowser.exceptions import HyperbrowserError


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
        if type(key) is str:
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
    key_display: Callable[[str], str],
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
            try:
                key_text = key_display(key)
                if type(key_text) is not str:
                    raise TypeError("mapping key display must be a string")
            except Exception:
                key_text = "<unreadable key>"
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
    key_display: Callable[[str], str],
) -> Dict[str, object]:
    normalized_mapping: Dict[str, object] = {}
    for key in keys:
        if type(key) is not str:
            raise HyperbrowserError("mapping key list must contain plain strings")
        try:
            normalized_mapping[key] = mapping_value[key]
        except HyperbrowserError:
            raise
        except Exception as exc:
            try:
                key_text = key_display(key)
                if type(key_text) is not str:
                    raise TypeError("mapping key display must be a string")
            except Exception:
                key_text = "<unreadable key>"
            raise HyperbrowserError(
                read_value_error_builder(key_text),
                original_error=exc,
            ) from exc
    return normalized_mapping
