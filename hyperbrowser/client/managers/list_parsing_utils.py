from typing import Any, Callable, List, TypeVar

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.mapping_utils import read_string_key_mapping, safe_key_display_for_error

T = TypeVar("T")


def read_plain_list_items(
    items_value: Any,
    *,
    expected_list_error: str,
    read_list_error: str,
) -> List[Any]:
    if type(items_value) is not list:
        raise HyperbrowserError(expected_list_error)
    try:
        return list(items_value)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(read_list_error, original_error=exc) from exc


def parse_mapping_list_items(
    items: List[Any],
    *,
    item_label: str,
    parse_item: Callable[[dict[str, object]], T],
    key_display: Callable[[str], str],
) -> List[T]:
    parsed_items: List[T] = []
    for index, item in enumerate(items):
        item_payload = read_string_key_mapping(
            item,
            expected_mapping_error=(
                f"Expected {item_label} object at index {index} but got {type(item).__name__}"
            ),
            read_keys_error=f"Failed to read {item_label} object at index {index}",
            non_string_key_error_builder=lambda _key: (
                f"Expected {item_label} object keys to be strings at index {index}"
            ),
            read_value_error_builder=lambda key_text: (
                f"Failed to read {item_label} object value for key '{key_text}' at index {index}"
            ),
            key_display=lambda key: safe_key_display_for_error(
                key, key_display=key_display
            ),
        )
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
