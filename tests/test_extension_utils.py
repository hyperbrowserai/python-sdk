import pytest
from types import MappingProxyType

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
        HyperbrowserError, match="Expected 'extensions' key in response but got \\[\\] keys"
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
