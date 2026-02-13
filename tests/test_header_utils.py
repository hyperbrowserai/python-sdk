import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.header_utils import normalize_headers, parse_headers_env_json


def test_normalize_headers_trims_header_names():
    headers = normalize_headers(
        {"  X-Correlation-Id  ": "abc123"},
        mapping_error_message="headers must be a mapping of string pairs",
    )

    assert headers == {"X-Correlation-Id": "abc123"}


def test_normalize_headers_rejects_empty_header_name():
    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        normalize_headers(
            {"   ": "value"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_normalize_headers_rejects_duplicate_names_after_normalization():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        normalize_headers(
            {"X-Trace-Id": "one", "  X-Trace-Id  ": "two"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_normalize_headers_rejects_case_insensitive_duplicate_names():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        normalize_headers(
            {"X-Trace-Id": "one", "x-trace-id": "two"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_parse_headers_env_json_ignores_blank_values():
    assert parse_headers_env_json("   ") is None


def test_parse_headers_env_json_rejects_non_string_input():
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be a string"
    ):
        parse_headers_env_json(123)  # type: ignore[arg-type]


def test_parse_headers_env_json_rejects_invalid_json():
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be valid JSON object"
    ):
        parse_headers_env_json("{invalid")


def test_parse_headers_env_json_rejects_non_mapping_payload():
    with pytest.raises(
        HyperbrowserError,
        match="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    ):
        parse_headers_env_json('["bad"]')
