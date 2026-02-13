from types import MappingProxyType

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


def test_client_config_rejects_empty_or_invalid_base_url():
    with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
        ClientConfig(api_key="test-key", base_url="   ")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig(api_key="test-key", base_url="api.hyperbrowser.ai")

    with pytest.raises(HyperbrowserError, match="include a host"):
        ClientConfig(api_key="test-key", base_url="http://")

    with pytest.raises(HyperbrowserError, match="must not include query parameters"):
        ClientConfig(api_key="test-key", base_url="https://example.local#frag")


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


def test_client_config_rejects_newline_header_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        ClientConfig(api_key="test-key", headers={"X-Correlation-Id": "bad\nvalue"})


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
