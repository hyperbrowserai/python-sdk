from collections.abc import Mapping
from typing import Iterator

import pytest

from hyperbrowser.client.managers.list_parsing_utils import parse_mapping_list_items
from hyperbrowser.exceptions import HyperbrowserError


class _ExplodingKeysMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        _ = key
        return "value"

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def keys(self):  # type: ignore[override]
        raise RuntimeError("broken keys")


class _ExplodingValueMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        _ = key
        raise RuntimeError("broken getitem")

    def __iter__(self) -> Iterator[object]:
        return iter(("field",))

    def __len__(self) -> int:
        return 1

    def keys(self):  # type: ignore[override]
        return ("field",)


def test_parse_mapping_list_items_parses_each_mapping():
    parsed = parse_mapping_list_items(
        [{"id": "a"}, {"id": "b"}],
        item_label="demo",
        parse_item=lambda payload: payload["id"],
        key_display=lambda key: key,
    )

    assert parsed == ["a", "b"]


def test_parse_mapping_list_items_rejects_non_mapping_items():
    with pytest.raises(
        HyperbrowserError, match="Expected demo object at index 0 but got list"
    ):
        parse_mapping_list_items(
            [[]],
            item_label="demo",
            parse_item=lambda payload: payload,
            key_display=lambda key: key,
        )


def test_parse_mapping_list_items_wraps_key_read_failures():
    with pytest.raises(
        HyperbrowserError, match="Failed to read demo object at index 0"
    ) as exc_info:
        parse_mapping_list_items(
            [_ExplodingKeysMapping()],
            item_label="demo",
            parse_item=lambda payload: payload,
            key_display=lambda key: key,
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_parse_mapping_list_items_rejects_non_string_keys():
    with pytest.raises(
        HyperbrowserError,
        match="Expected demo object keys to be strings at index 0",
    ):
        parse_mapping_list_items(
            [{1: "value"}],
            item_label="demo",
            parse_item=lambda payload: payload,
            key_display=lambda key: key,
        )


def test_parse_mapping_list_items_wraps_value_read_failures():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read demo object value for key 'field' at index 0",
    ) as exc_info:
        parse_mapping_list_items(
            [_ExplodingValueMapping()],
            item_label="demo",
            parse_item=lambda payload: payload,
            key_display=lambda key: key,
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_parse_mapping_list_items_falls_back_when_key_display_raises():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read demo object value for key '<unreadable key>' at index 0",
    ):
        parse_mapping_list_items(
            [_ExplodingValueMapping()],
            item_label="demo",
            parse_item=lambda payload: payload,
            key_display=lambda key: 1 / 0,
        )


def test_parse_mapping_list_items_falls_back_when_key_display_returns_non_string():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read demo object value for key '<unreadable key>' at index 0",
    ):
        parse_mapping_list_items(
            [_ExplodingValueMapping()],
            item_label="demo",
            parse_item=lambda payload: payload,
            key_display=lambda key: key.encode("utf-8"),
        )


def test_parse_mapping_list_items_wraps_parse_failures():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to parse demo at index 0",
    ) as exc_info:
        parse_mapping_list_items(
            [{"id": "x"}],
            item_label="demo",
            parse_item=lambda payload: 1 / 0,
            key_display=lambda key: key,
        )

    assert isinstance(exc_info.value.original_error, ZeroDivisionError)
