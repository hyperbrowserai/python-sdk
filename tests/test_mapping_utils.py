from collections.abc import Iterator, Mapping

import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.mapping_utils import (
    copy_mapping_values_by_string_keys,
    read_string_mapping_keys,
    read_string_key_mapping,
    safe_key_display_for_error,
)


class _BrokenKeysMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        _ = key
        return "value"

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def keys(self):  # type: ignore[override]
        raise RuntimeError("broken keys")


class _HyperbrowserKeysFailureMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        _ = key
        return "value"

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def keys(self):  # type: ignore[override]
        raise HyperbrowserError("custom keys failure")


class _BrokenValueMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        _ = key
        raise RuntimeError("broken value read")

    def __iter__(self) -> Iterator[object]:
        return iter(("field",))

    def __len__(self) -> int:
        return 1


class _HyperbrowserValueFailureMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        _ = key
        raise HyperbrowserError("custom value read failure")

    def __iter__(self) -> Iterator[object]:
        return iter(("field",))

    def __len__(self) -> int:
        return 1


def _read_mapping(mapping_value):
    return read_string_key_mapping(
        mapping_value,
        expected_mapping_error="expected mapping",
        read_keys_error="failed keys",
        non_string_key_error_builder=lambda key: (
            f"non-string key: {type(key).__name__}"
        ),
        read_value_error_builder=lambda key_display: (
            f"failed value for '{key_display}'"
        ),
        key_display=lambda key: key,
    )


def test_read_string_key_mapping_returns_dict():
    assert _read_mapping({"field": "value"}) == {"field": "value"}


def test_read_string_key_mapping_rejects_non_mappings():
    with pytest.raises(HyperbrowserError, match="expected mapping"):
        _read_mapping(["value"])


def test_read_string_key_mapping_wraps_key_iteration_failures():
    with pytest.raises(HyperbrowserError, match="failed keys") as exc_info:
        _read_mapping(_BrokenKeysMapping())

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_read_string_key_mapping_rejects_non_string_keys():
    with pytest.raises(HyperbrowserError, match="non-string key: int"):
        _read_mapping({1: "value"})


def test_read_string_key_mapping_wraps_value_read_failures():
    with pytest.raises(HyperbrowserError, match="failed value for 'field'") as exc_info:
        _read_mapping(_BrokenValueMapping())

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_read_string_key_mapping_preserves_hyperbrowser_value_failures():
    with pytest.raises(
        HyperbrowserError, match="custom value read failure"
    ) as exc_info:
        _read_mapping(_HyperbrowserValueFailureMapping())

    assert exc_info.value.original_error is None


def test_read_string_key_mapping_falls_back_for_unreadable_key_display():
    with pytest.raises(HyperbrowserError, match="failed value for '<unreadable key>'"):
        read_string_key_mapping(
            _BrokenValueMapping(),
            expected_mapping_error="expected mapping",
            read_keys_error="failed keys",
            non_string_key_error_builder=lambda key: (
                f"non-string key: {type(key).__name__}"
            ),
            read_value_error_builder=lambda key_display: (
                f"failed value for '{key_display}'"
            ),
            key_display=lambda key: key.encode("utf-8"),
        )


def test_safe_key_display_for_error_returns_display_value():
    assert (
        safe_key_display_for_error("field", key_display=lambda key: f"<{key}>")
        == "<field>"
    )


def test_safe_key_display_for_error_returns_unreadable_key_on_failures():
    assert (
        safe_key_display_for_error(
            "field",
            key_display=lambda key: key.encode("utf-8"),
        )
        == "<unreadable key>"
    )


def test_read_string_mapping_keys_returns_string_keys():
    assert read_string_mapping_keys(
        {"a": 1, "b": 2},
        expected_mapping_error="expected mapping",
        read_keys_error="failed keys",
        non_string_key_error_builder=lambda key: (
            f"non-string key: {type(key).__name__}"
        ),
    ) == ["a", "b"]


def test_read_string_mapping_keys_rejects_non_mapping_values():
    with pytest.raises(HyperbrowserError, match="expected mapping"):
        read_string_mapping_keys(
            ["a"],
            expected_mapping_error="expected mapping",
            read_keys_error="failed keys",
            non_string_key_error_builder=lambda key: (
                f"non-string key: {type(key).__name__}"
            ),
        )


def test_read_string_mapping_keys_wraps_key_read_errors():
    with pytest.raises(HyperbrowserError, match="failed keys") as exc_info:
        read_string_mapping_keys(
            _BrokenKeysMapping(),
            expected_mapping_error="expected mapping",
            read_keys_error="failed keys",
            non_string_key_error_builder=lambda key: (
                f"non-string key: {type(key).__name__}"
            ),
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_read_string_mapping_keys_rejects_non_string_keys():
    with pytest.raises(HyperbrowserError, match="non-string key: int"):
        read_string_mapping_keys(
            {1: "value"},
            expected_mapping_error="expected mapping",
            read_keys_error="failed keys",
            non_string_key_error_builder=lambda key: (
                f"non-string key: {type(key).__name__}"
            ),
        )


def test_read_string_mapping_keys_rejects_string_subclass_keys():
    class _StringKey(str):
        pass

    with pytest.raises(HyperbrowserError, match="non-string key: _StringKey"):
        read_string_mapping_keys(
            {_StringKey("key"): "value"},
            expected_mapping_error="expected mapping",
            read_keys_error="failed keys",
            non_string_key_error_builder=lambda key: (
                f"non-string key: {type(key).__name__}"
            ),
        )


def test_read_string_mapping_keys_preserves_hyperbrowser_key_read_failures():
    with pytest.raises(HyperbrowserError, match="custom keys failure") as exc_info:
        read_string_mapping_keys(
            _HyperbrowserKeysFailureMapping(),
            expected_mapping_error="expected mapping",
            read_keys_error="failed keys",
            non_string_key_error_builder=lambda key: (
                f"non-string key: {type(key).__name__}"
            ),
        )

    assert exc_info.value.original_error is None


def test_copy_mapping_values_by_string_keys_returns_selected_values():
    copied_values = copy_mapping_values_by_string_keys(
        {"field": "value", "other": "ignored"},
        ["field"],
        read_value_error_builder=lambda key_display: (
            f"failed value for '{key_display}'"
        ),
        key_display=lambda key: key,
    )

    assert copied_values == {"field": "value"}


def test_copy_mapping_values_by_string_keys_wraps_value_read_failures():
    with pytest.raises(HyperbrowserError, match="failed value for 'field'") as exc_info:
        copy_mapping_values_by_string_keys(
            _BrokenValueMapping(),
            ["field"],
            read_value_error_builder=lambda key_display: (
                f"failed value for '{key_display}'"
            ),
            key_display=lambda key: key,
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_copy_mapping_values_by_string_keys_preserves_hyperbrowser_failures():
    with pytest.raises(
        HyperbrowserError, match="custom value read failure"
    ) as exc_info:
        copy_mapping_values_by_string_keys(
            _HyperbrowserValueFailureMapping(),
            ["field"],
            read_value_error_builder=lambda key_display: (
                f"failed value for '{key_display}'"
            ),
            key_display=lambda key: key,
        )

    assert exc_info.value.original_error is None


def test_copy_mapping_values_by_string_keys_falls_back_for_unreadable_key_display():
    with pytest.raises(HyperbrowserError, match="failed value for '<unreadable key>'"):
        copy_mapping_values_by_string_keys(
            _BrokenValueMapping(),
            ["field"],
            read_value_error_builder=lambda key_display: (
                f"failed value for '{key_display}'"
            ),
            key_display=lambda key: key.encode("utf-8"),
        )


def test_copy_mapping_values_by_string_keys_rejects_string_subclass_keys():
    class _StringKey(str):
        pass

    with pytest.raises(
        HyperbrowserError, match="mapping key list must contain plain strings"
    ) as exc_info:
        copy_mapping_values_by_string_keys(
            {"key": "value"},
            [_StringKey("key")],  # type: ignore[list-item]
            read_value_error_builder=lambda key_display: (
                f"failed value for '{key_display}'"
            ),
            key_display=lambda key: key,
        )

    assert exc_info.value.original_error is None
