import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.header_utils import (
    merge_headers,
    normalize_headers,
    parse_headers_env_json,
)


class _BrokenHeadersMapping(dict):
    def items(self):
        raise RuntimeError("broken header iteration")


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


def test_normalize_headers_rejects_overly_long_header_names():
    long_header_name = "X-" + ("a" * 255)
    with pytest.raises(
        HyperbrowserError, match="header names must be 256 characters or fewer"
    ):
        normalize_headers(
            {long_header_name: "value"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_normalize_headers_rejects_invalid_header_name_characters():
    with pytest.raises(
        HyperbrowserError,
        match="header names must contain only valid HTTP token characters",
    ):
        normalize_headers(
            {"X Trace Id": "value"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_normalize_headers_accepts_valid_http_token_characters():
    headers = normalize_headers(
        {"X-Test_!#$%&'*+-.^`|~": "value"},
        mapping_error_message="headers must be a mapping of string pairs",
    )

    assert headers == {"X-Test_!#$%&'*+-.^`|~": "value"}


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


def test_parse_headers_env_json_wraps_recursive_json_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_recursion_error(_raw_headers: str):
        raise RecursionError("nested too deeply")

    monkeypatch.setattr("hyperbrowser.header_utils.json.loads", _raise_recursion_error)

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be valid JSON object"
    ):
        parse_headers_env_json('{"X-Trace-Id":"abc123"}')


def test_parse_headers_env_json_rejects_non_mapping_payload():
    with pytest.raises(
        HyperbrowserError,
        match="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    ):
        parse_headers_env_json('["bad"]')


def test_parse_headers_env_json_rejects_invalid_header_name_characters():
    with pytest.raises(
        HyperbrowserError,
        match="header names must contain only valid HTTP token characters",
    ):
        parse_headers_env_json('{"X Trace Id":"abc123"}')


def test_normalize_headers_rejects_control_characters():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain control characters"
    ):
        normalize_headers(
            {"X-Trace-Id": "value\twith-tab"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_parse_headers_env_json_rejects_control_characters():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain control characters"
    ):
        parse_headers_env_json('{"X-Trace-Id":"bad\\u0000value"}')


def test_merge_headers_replaces_existing_headers_case_insensitively():
    merged = merge_headers(
        {"User-Agent": "default-sdk", "x-api-key": "test-key"},
        {"user-agent": "custom-sdk", "X-API-KEY": "override-key"},
        mapping_error_message="headers must be a mapping of string pairs",
    )

    assert merged["user-agent"] == "custom-sdk"
    assert merged["X-API-KEY"] == "override-key"
    assert "User-Agent" not in merged
    assert "x-api-key" not in merged


def test_merge_headers_rejects_invalid_base_header_pairs():
    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        merge_headers(
            {"x-api-key": 123},  # type: ignore[dict-item]
            {"User-Agent": "custom"},
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_merge_headers_rejects_duplicate_base_header_names_case_insensitive():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        merge_headers(
            {"X-Request-Id": "one", "x-request-id": "two"},
            None,
            mapping_error_message="headers must be a mapping of string pairs",
        )


def test_normalize_headers_wraps_mapping_iteration_failures():
    with pytest.raises(
        HyperbrowserError, match="headers must be a mapping of string pairs"
    ) as exc_info:
        normalize_headers(
            _BrokenHeadersMapping({"X-Trace-Id": "abc123"}),
            mapping_error_message="headers must be a mapping of string pairs",
        )

    assert exc_info.value.original_error is not None


def test_merge_headers_wraps_override_mapping_iteration_failures():
    with pytest.raises(
        HyperbrowserError, match="headers must be a mapping of string pairs"
    ) as exc_info:
        merge_headers(
            {"X-Trace-Id": "abc123"},
            _BrokenHeadersMapping({"X-Correlation-Id": "corr-1"}),
            mapping_error_message="headers must be a mapping of string pairs",
        )

    assert exc_info.value.original_error is not None
