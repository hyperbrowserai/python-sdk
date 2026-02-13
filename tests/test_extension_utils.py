import pytest

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
    with pytest.raises(HyperbrowserError, match="Expected dict response"):
        parse_extension_list_response_data(["not-a-dict"])  # type: ignore[arg-type]


def test_parse_extension_list_response_data_rejects_missing_extensions_key():
    with pytest.raises(HyperbrowserError, match="Expected 'extensions' key"):
        parse_extension_list_response_data({})


def test_parse_extension_list_response_data_rejects_non_list_extensions():
    with pytest.raises(HyperbrowserError, match="Expected list in 'extensions' key"):
        parse_extension_list_response_data({"extensions": "not-a-list"})
