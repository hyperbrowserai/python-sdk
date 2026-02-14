from collections.abc import Iterator, Mapping

import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.mapping_utils import read_string_key_mapping


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
        non_string_key_error_builder=lambda key: f"non-string key: {type(key).__name__}",
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
    with pytest.raises(
        HyperbrowserError, match="failed value for 'field'"
    ) as exc_info:
        _read_mapping(_BrokenValueMapping())

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_read_string_key_mapping_preserves_hyperbrowser_value_failures():
    with pytest.raises(HyperbrowserError, match="custom value read failure") as exc_info:
        _read_mapping(_HyperbrowserValueFailureMapping())

    assert exc_info.value.original_error is None


def test_read_string_key_mapping_falls_back_for_unreadable_key_display():
    with pytest.raises(
        HyperbrowserError, match="failed value for '<unreadable key>'"
    ):
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
