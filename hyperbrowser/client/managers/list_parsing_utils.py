from collections.abc import Mapping
from typing import Any, Callable, List, TypeVar

from hyperbrowser.exceptions import HyperbrowserError

T = TypeVar("T")


def _safe_key_display_for_error(
    key: str,
    *,
    key_display: Callable[[str], str],
) -> str:
    try:
        key_text = key_display(key)
        if type(key_text) is not str:
            raise TypeError("key display must be a string")
        return key_text
    except Exception:
        return "<unreadable key>"


def parse_mapping_list_items(
    items: List[Any],
    *,
    item_label: str,
    parse_item: Callable[[dict[str, object]], T],
    key_display: Callable[[str], str],
) -> List[T]:
    parsed_items: List[T] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise HyperbrowserError(
                f"Expected {item_label} object at index {index} but got {type(item).__name__}"
            )
        try:
            item_keys = list(item.keys())
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {item_label} object at index {index}",
                original_error=exc,
            ) from exc
        for key in item_keys:
            if type(key) is str:
                continue
            raise HyperbrowserError(
                f"Expected {item_label} object keys to be strings at index {index}"
            )
        item_payload: dict[str, object] = {}
        for key in item_keys:
            try:
                item_payload[key] = item[key]
            except HyperbrowserError:
                raise
            except Exception as exc:
                key_text = _safe_key_display_for_error(key, key_display=key_display)
                raise HyperbrowserError(
                    f"Failed to read {item_label} object value for key '{key_text}' at index {index}",
                    original_error=exc,
                ) from exc
        try:
            parsed_items.append(parse_item(item_payload))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to parse {item_label} at index {index}",
                original_error=exc,
            ) from exc
    return parsed_items
