from types import MappingProxyType
from urllib.parse import quote

import pytest

from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError


def test_client_config_from_env_raises_hyperbrowser_error_without_api_key(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_raises_hyperbrowser_error_for_blank_api_key(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "   ")

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_control_character_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "bad\nkey")

    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_reads_api_key_and_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://example.local")

    config = ClientConfig.from_env()

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"


def test_client_config_from_env_reads_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Request-Id":"abc123"}')

    config = ClientConfig.from_env()

    assert config.headers == {"X-Request-Id": "abc123"}


def test_client_config_from_env_rejects_invalid_headers_json(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be valid JSON object"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_non_object_headers_json(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '["not-an-object"]')

    with pytest.raises(
        HyperbrowserError,
        match="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_non_string_header_values(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Request-Id":123}')

    with pytest.raises(
        HyperbrowserError,
        match="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_empty_header_name(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"   ":"value"}')

    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_newline_header_values(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Correlation-Id":"bad\\nvalue"}')

    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_duplicate_header_names_after_normalization(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv(
        "HYPERBROWSER_HEADERS",
        '{"X-Correlation-Id":"one","  X-Correlation-Id  ":"two"}',
    )

    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_case_insensitive_duplicate_header_names(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv(
        "HYPERBROWSER_HEADERS",
        '{"X-Correlation-Id":"one","x-correlation-id":"two"}',
    )

    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig.from_env()


def test_client_config_from_env_ignores_blank_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "   ")

    config = ClientConfig.from_env()

    assert config.headers is None


def test_client_config_from_env_normalizes_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", " https://example.local/ ")

    config = ClientConfig.from_env()

    assert config.base_url == "https://example.local"


def test_client_config_from_env_rejects_invalid_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "example.local")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_blank_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "   ")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_base_url_without_host(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://")

    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig.from_env()


def test_client_config_from_env_rejects_base_url_query_or_fragment(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://example.local?x=1")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig.from_env()


def test_client_config_normalizes_whitespace_and_trailing_slash():
    config = ClientConfig(api_key="  test-key  ", base_url=" https://example.local/ ")

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"


def test_client_config_rejects_non_string_values():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        ClientConfig(api_key=None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="base_url must be a string"):
        ClientConfig(api_key="test-key", base_url=None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        ClientConfig(api_key="test-key", headers="x=1")  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        ClientConfig(api_key="   ")
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        ClientConfig(api_key="bad\nkey")


def test_client_config_rejects_empty_or_invalid_base_url():
    with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
        ClientConfig(api_key="test-key", base_url="   ")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig(api_key="test-key", base_url="api.hyperbrowser.ai")

    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig(api_key="test-key", base_url="http://")
    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig(api_key="test-key", base_url="https://:443")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local:99999")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local:bad")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig(api_key="test-key", base_url="https://example.local#frag")
    with pytest.raises(
        HyperbrowserError, match="base_url must not include user credentials"
    ):
        ClientConfig(api_key="test-key", base_url="https://user:pass@example.local")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain newline characters"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local/\napi")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain whitespace characters"
    ):
        ClientConfig(api_key="test-key", base_url="https://example .local")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain backslashes"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local\\api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain control characters"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local\x00api")
    with pytest.raises(
        HyperbrowserError, match="base_url path must not contain relative path segments"
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local/%2e%2e/api")
    with pytest.raises(
        HyperbrowserError,
        match="base_url path must not contain encoded query or fragment delimiters",
    ):
        ClientConfig(api_key="test-key", base_url="https://example.local/%3Fapi")


def test_client_config_normalizes_headers_to_internal_copy():
    headers = {"X-Correlation-Id": "abc123"}
    config = ClientConfig(api_key="test-key", headers=headers)

    headers["X-Correlation-Id"] = "changed"

    assert config.headers == {"X-Correlation-Id": "abc123"}


def test_client_config_rejects_non_string_header_pairs():
    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": 123})  # type: ignore[dict-item]


def test_client_config_rejects_empty_header_name():
    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        ClientConfig(api_key="test-key", headers={"   ": "value"})


def test_client_config_rejects_invalid_header_name_characters():
    with pytest.raises(
        HyperbrowserError,
        match="header names must contain only valid HTTP token characters",
    ):
        ClientConfig(api_key="test-key", headers={"X Trace": "value"})


def test_client_config_rejects_newline_header_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": "bad\nvalue"})


def test_client_config_rejects_control_character_header_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain control characters"
    ):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": "bad\tvalue"})


def test_client_config_normalizes_header_name_whitespace():
    config = ClientConfig(api_key="test-key", headers={"  X-Correlation-Id  ": "value"})

    assert config.headers == {"X-Correlation-Id": "value"}


def test_client_config_rejects_duplicate_header_names_after_normalization():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig(
            api_key="test-key",
            headers={"X-Correlation-Id": "one", "  X-Correlation-Id  ": "two"},
        )


def test_client_config_rejects_case_insensitive_duplicate_header_names():
    with pytest.raises(
        HyperbrowserError,
        match="duplicate header names are not allowed after normalization",
    ):
        ClientConfig(
            api_key="test-key",
            headers={"X-Correlation-Id": "one", "x-correlation-id": "two"},
        )


def test_client_config_accepts_mapping_header_inputs():
    headers = MappingProxyType({"X-Correlation-Id": "abc123"})
    config = ClientConfig(api_key="test-key", headers=headers)

    assert config.headers == {"X-Correlation-Id": "abc123"}


def test_client_config_parse_headers_from_env_rejects_non_string_input():
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_HEADERS must be a string"
    ):
        ClientConfig.parse_headers_from_env(123)  # type: ignore[arg-type]


def test_client_config_resolve_base_url_from_env_defaults_and_rejects_blank():
    assert ClientConfig.resolve_base_url_from_env(None) == "https://api.hyperbrowser.ai"
    assert (
        ClientConfig.resolve_base_url_from_env("https://example.local")
        == "https://example.local"
    )
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        ClientConfig.resolve_base_url_from_env("   ")
    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig.resolve_base_url_from_env("https://")
    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must be a string"
    ):
        ClientConfig.resolve_base_url_from_env(123)  # type: ignore[arg-type]


def test_client_config_normalize_base_url_validates_and_normalizes():
    assert (
        ClientConfig.normalize_base_url(" https://example.local/custom/api/ ")
        == "https://example.local/custom/api"
    )
    assert (
        ClientConfig.normalize_base_url("https://example.local:443/custom/api")
        == "https://example.local:443/custom/api"
    )

    with pytest.raises(HyperbrowserError, match="base_url must be a string"):
        ClientConfig.normalize_base_url(None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
        ClientConfig.normalize_base_url("   ")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig.normalize_base_url("example.local")
    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig.normalize_base_url("https://:443")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig.normalize_base_url("https://example.local:99999")
    with pytest.raises(
        HyperbrowserError, match="base_url must contain a valid port number"
    ):
        ClientConfig.normalize_base_url("https://example.local:bad")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig.normalize_base_url("https://example.local?foo=bar")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain newline characters"
    ):
        ClientConfig.normalize_base_url("https://example.local/\napi")

    with pytest.raises(
        HyperbrowserError, match="base_url must not contain whitespace characters"
    ):
        ClientConfig.normalize_base_url("https://example.local/\tapi")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain backslashes"
    ):
        ClientConfig.normalize_base_url("https://example.local\\api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain control characters"
    ):
        ClientConfig.normalize_base_url("https://example.local\x00api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not include user credentials"
    ):
        ClientConfig.normalize_base_url("https://user:pass@example.local")
    with pytest.raises(
        HyperbrowserError, match="base_url path must not contain relative path segments"
    ):
        ClientConfig.normalize_base_url("https://example.local/%252e%252e/api")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain backslashes"
    ):
        ClientConfig.normalize_base_url("https://example.local/%255Capi")
    with pytest.raises(
        HyperbrowserError, match="base_url must not contain whitespace characters"
    ):
        ClientConfig.normalize_base_url("https://example.local/%2520api")
    with pytest.raises(
        HyperbrowserError, match="base_url host must not contain backslashes"
    ):
        ClientConfig.normalize_base_url("https://example.local%255C")
    with pytest.raises(
        HyperbrowserError, match="base_url host must not contain whitespace characters"
    ):
        ClientConfig.normalize_base_url("https://example.local%2520")
    with pytest.raises(
        HyperbrowserError, match="base_url host must not contain control characters"
    ):
        ClientConfig.normalize_base_url("https://example.local%2500")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host must not contain encoded delimiter characters",
    ):
        ClientConfig.normalize_base_url("https://example.local%252Fapi")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host must not contain encoded delimiter characters",
    ):
        ClientConfig.normalize_base_url("https://example.local%2540attacker.com")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host must not contain encoded delimiter characters",
    ):
        ClientConfig.normalize_base_url("https://example.local%253A443")
    with pytest.raises(
        HyperbrowserError,
        match="base_url path must not contain encoded query or fragment delimiters",
    ):
        ClientConfig.normalize_base_url("https://example.local/%253Fapi")
    deeply_encoded_dot = "%2e"
    for _ in range(11):
        deeply_encoded_dot = quote(deeply_encoded_dot, safe="")
    with pytest.raises(
        HyperbrowserError,
        match="base_url path contains excessively nested URL encoding",
    ):
        ClientConfig.normalize_base_url(
            f"https://example.local/{deeply_encoded_dot}/api"
        )
    deeply_encoded_host_label = "%61"
    for _ in range(11):
        deeply_encoded_host_label = quote(deeply_encoded_host_label, safe="")
    with pytest.raises(
        HyperbrowserError,
        match="base_url host contains excessively nested URL encoding",
    ):
        ClientConfig.normalize_base_url(
            f"https://{deeply_encoded_host_label}.example.local"
        )
