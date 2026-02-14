from collections.abc import Iterator, Mapping
from types import MappingProxyType

import pytest

from hyperbrowser.client.managers import extension_utils
from hyperbrowser.client.managers.extension_utils import (
    parse_extension_list_response_data,
)
from hyperbrowser.exceptions import HyperbrowserError


def test_parse_extension_list_response_data_parses_extensions():
    parsed = parse_extension_list_response_data(
        {
            "extensions": [
                {
                    "id": "ext_123",
                    "name": "my-extension",
                    "createdAt": "2026-01-01T00:00:00Z",
                    "updatedAt": "2026-01-01T00:00:00Z",
                }
            ]
        }
    )

    assert len(parsed) == 1
    assert parsed[0].id == "ext_123"


def test_parse_extension_list_response_data_rejects_non_dict_payload():
    with pytest.raises(HyperbrowserError, match="Expected mapping response"):
        parse_extension_list_response_data(["not-a-dict"])  # type: ignore[arg-type]


def test_parse_extension_list_response_data_rejects_missing_extensions_key():
    with pytest.raises(
        HyperbrowserError,
        match="Expected 'extensions' key in response but got \\[\\] keys",
    ):
        parse_extension_list_response_data({})


def test_parse_extension_list_response_data_rejects_non_list_extensions():
    with pytest.raises(HyperbrowserError, match="Expected list in 'extensions' key"):
        parse_extension_list_response_data({"extensions": "not-a-list"})


def test_parse_extension_list_response_data_rejects_non_object_extension_items():
    with pytest.raises(HyperbrowserError, match="Expected extension object at index 0"):
        parse_extension_list_response_data({"extensions": ["not-an-object"]})


def test_parse_extension_list_response_data_wraps_invalid_extension_payloads():
    with pytest.raises(HyperbrowserError, match="Failed to parse extension at index 0"):
        parse_extension_list_response_data(
            {
                "extensions": [
                    {
                        "id": "ext_123",
                        # missing required fields: name/createdAt/updatedAt
                    }
                ]
            }
        )


def test_parse_extension_list_response_data_preserves_hyperbrowser_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    class _RaisingExtensionResponse:
        def __init__(self, **kwargs):
            _ = kwargs
            raise HyperbrowserError("extension parse failed")

    monkeypatch.setattr(
        extension_utils,
        "ExtensionResponse",
        _RaisingExtensionResponse,
    )

    with pytest.raises(HyperbrowserError, match="extension parse failed") as exc_info:
        parse_extension_list_response_data({"extensions": [{"id": "ext_1"}]})

    assert exc_info.value.original_error is None


def test_parse_extension_list_response_data_accepts_mapping_proxy_payload():
    extension_mapping = MappingProxyType(
        {
            "id": "ext_123",
            "name": "my-extension",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
    )
    payload = MappingProxyType({"extensions": [extension_mapping]})

    parsed = parse_extension_list_response_data(payload)

    assert len(parsed) == 1
    assert parsed[0].id == "ext_123"


def test_parse_extension_list_response_data_missing_key_lists_available_keys():
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Expected 'extensions' key in response but got "
            "\\[createdAt, id, name, updatedAt\\] keys"
        ),
    ):
        parse_extension_list_response_data(
            {
                "id": "ext_123",
                "name": "my-extension",
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
            }
        )


def test_parse_extension_list_response_data_missing_key_limits_key_list_size():
    payload = {f"key-{index:02d}": index for index in range(25)}

    with pytest.raises(
        HyperbrowserError,
        match=(
            "Expected 'extensions' key in response but got "
            r"\[key-00, key-01, key-02, key-03, key-04, key-05, key-06, key-07,"
            r" key-08, key-09, key-10, key-11, key-12, key-13, key-14, key-15,"
            r" key-16, key-17, key-18, key-19, \.\.\. \(\+5 more\)\] keys"
        ),
    ):
        parse_extension_list_response_data(payload)


def test_parse_extension_list_response_data_missing_key_truncates_long_key_names():
    long_key = "k" * 160
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Expected 'extensions' key in response but got "
            r"\[k{105}\.\.\. \(truncated\)\] keys"
        ),
    ):
        parse_extension_list_response_data({long_key: "value"})


def test_parse_extension_list_response_data_missing_key_normalizes_blank_key_names():
    with pytest.raises(
        HyperbrowserError,
        match="Expected 'extensions' key in response but got \\[<blank key>\\] keys",
    ):
        parse_extension_list_response_data({"   ": "value"})


def test_parse_extension_list_response_data_missing_key_normalizes_control_characters():
    with pytest.raises(
        HyperbrowserError,
        match="Expected 'extensions' key in response but got \\[bad\\?key\\] keys",
    ):
        parse_extension_list_response_data({"bad\tkey": "value"})


def test_parse_extension_list_response_data_missing_key_handles_unprintable_keys():
    class _BrokenStringKey:
        def __str__(self) -> str:
            raise RuntimeError("bad key stringification")

    with pytest.raises(
        HyperbrowserError,
        match=(
            "Expected 'extensions' key in response but got "
            "\\[<unprintable _BrokenStringKey>\\] keys"
        ),
    ):
        parse_extension_list_response_data({_BrokenStringKey(): "value"})


def test_parse_extension_list_response_data_missing_key_handles_string_subclass_str_results():
    class _StringSubclassKey:
        class _RenderedKey(str):
            pass

        def __str__(self) -> str:
            return self._RenderedKey("subclass-key")

    with pytest.raises(
        HyperbrowserError,
        match=(
            "Expected 'extensions' key in response but got "
            "\\[<unprintable _StringSubclassKey>\\] keys"
        ),
    ):
        parse_extension_list_response_data({_StringSubclassKey(): "value"})


def test_parse_extension_list_response_data_missing_key_handles_unreadable_keys():
    class _BrokenKeysMapping(dict):
        def keys(self):
            raise RuntimeError("cannot read keys")

    with pytest.raises(
        HyperbrowserError,
        match="Expected 'extensions' key in response but got \\[<unavailable keys>\\] keys",
    ):
        parse_extension_list_response_data(_BrokenKeysMapping({"id": "ext_1"}))


def test_parse_extension_list_response_data_wraps_unreadable_extensions_membership():
    class _BrokenContainsMapping(dict):
        def __contains__(self, key: object) -> bool:
            _ = key
            raise RuntimeError("cannot inspect contains")

    with pytest.raises(
        HyperbrowserError, match="Failed to inspect response for 'extensions' key"
    ) as exc_info:
        parse_extension_list_response_data(_BrokenContainsMapping({"id": "ext_1"}))

    assert exc_info.value.original_error is not None


def test_parse_extension_list_response_data_preserves_hyperbrowser_contains_errors():
    class _BrokenContainsMapping(dict):
        def __contains__(self, key: object) -> bool:
            _ = key
            raise HyperbrowserError("custom contains failure")

    with pytest.raises(HyperbrowserError, match="custom contains failure") as exc_info:
        parse_extension_list_response_data(_BrokenContainsMapping({"id": "ext_1"}))

    assert exc_info.value.original_error is None


def test_parse_extension_list_response_data_wraps_unreadable_extensions_value():
    class _BrokenExtensionsLookupMapping(dict):
        def __contains__(self, key: object) -> bool:
            return key == "extensions"

        def __getitem__(self, key: object):
            if key == "extensions":
                raise RuntimeError("cannot read extensions value")
            return super().__getitem__(key)

    with pytest.raises(
        HyperbrowserError, match="Failed to read 'extensions' value from response"
    ) as exc_info:
        parse_extension_list_response_data(
            _BrokenExtensionsLookupMapping({"extensions": []})
        )

    assert exc_info.value.original_error is not None


def test_parse_extension_list_response_data_rejects_list_subclass_extensions_values():
    class _BrokenExtensionsList(list):
        def __iter__(self):
            raise RuntimeError("cannot iterate extensions list")

    with pytest.raises(
        HyperbrowserError, match="Expected list in 'extensions' key but got"
    ) as exc_info:
        parse_extension_list_response_data({"extensions": _BrokenExtensionsList([{}])})

    assert exc_info.value.original_error is None


def test_parse_extension_list_response_data_wraps_unreadable_extension_object():
    class _BrokenExtensionMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            raise RuntimeError("cannot iterate extension object")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            return "ignored"

    with pytest.raises(
        HyperbrowserError, match="Failed to read extension object at index 0"
    ) as exc_info:
        parse_extension_list_response_data({"extensions": [_BrokenExtensionMapping()]})

    assert exc_info.value.original_error is not None


def test_parse_extension_list_response_data_preserves_hyperbrowser_extension_read_errors():
    class _BrokenExtensionMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            raise HyperbrowserError("custom extension read failure")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            return "ignored"

    with pytest.raises(
        HyperbrowserError, match="custom extension read failure"
    ) as exc_info:
        parse_extension_list_response_data({"extensions": [_BrokenExtensionMapping()]})

    assert exc_info.value.original_error is None


def test_parse_extension_list_response_data_rejects_non_string_extension_keys():
    with pytest.raises(
        HyperbrowserError,
        match="Expected extension object keys to be strings at index 0",
    ):
        parse_extension_list_response_data(
            {
                "extensions": [
                    {1: "invalid-key"},  # type: ignore[dict-item]
                ]
            }
        )


def test_parse_extension_list_response_data_rejects_string_subclass_extension_keys():
    class _Key(str):
        pass

    with pytest.raises(
        HyperbrowserError,
        match="Expected extension object keys to be strings at index 0",
    ):
        parse_extension_list_response_data(
            {
                "extensions": [
                    {_Key("name"): "invalid-key-type"},
                ]
            }
        )


def test_parse_extension_list_response_data_wraps_extension_value_read_failures():
    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "name"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read extension value")

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read extension object value for key 'name' at index 0",
    ) as exc_info:
        parse_extension_list_response_data(
            {"extensions": [_BrokenValueLookupMapping()]}
        )

    assert exc_info.value.original_error is not None


def test_parse_extension_list_response_data_sanitizes_extension_value_read_keys():
    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "bad\tkey"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read extension value")

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read extension object value for key 'bad\\?key' at index 0",
    ) as exc_info:
        parse_extension_list_response_data(
            {"extensions": [_BrokenValueLookupMapping()]}
        )

    assert exc_info.value.original_error is not None


def test_parse_extension_list_response_data_rejects_string_subclass_value_read_keys():
    class _BrokenKey(str):
        class _BrokenRenderedKey(str):
            def __iter__(self):
                raise RuntimeError("cannot iterate rendered extension key")

        def __str__(self) -> str:
            return self._BrokenRenderedKey("name")

    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield _BrokenKey("name")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read extension value")

    with pytest.raises(
        HyperbrowserError,
        match="Expected extension object keys to be strings at index 0",
    ) as exc_info:
        parse_extension_list_response_data(
            {"extensions": [_BrokenValueLookupMapping()]}
        )

    assert exc_info.value.original_error is None


def test_parse_extension_list_response_data_preserves_hyperbrowser_value_read_errors():
    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "name"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise HyperbrowserError("custom extension value read failure")

    with pytest.raises(
        HyperbrowserError, match="custom extension value read failure"
    ) as exc_info:
        parse_extension_list_response_data(
            {"extensions": [_BrokenValueLookupMapping()]}
        )

    assert exc_info.value.original_error is None
