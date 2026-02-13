import pytest

from hyperbrowser import Hyperbrowser
from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError


def test_client_build_url_normalizes_leading_slash():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        assert (
            client._build_url("/session") == "https://api.hyperbrowser.ai/api/session"
        )
        assert client._build_url("session") == "https://api.hyperbrowser.ai/api/session"
        assert (
            client._build_url("/api/session")
            == "https://api.hyperbrowser.ai/api/session"
        )
        assert (
            client._build_url("api/session")
            == "https://api.hyperbrowser.ai/api/session"
        )
        assert (
            client._build_url("/api?foo=bar")
            == "https://api.hyperbrowser.ai/api?foo=bar"
        )
        assert (
            client._build_url("//api/session")
            == "https://api.hyperbrowser.ai/api/session"
        )
        assert (
            client._build_url("///session") == "https://api.hyperbrowser.ai/api/session"
        )
    finally:
        client.close()


def test_client_build_url_uses_normalized_base_url():
    client = Hyperbrowser(
        config=ClientConfig(api_key="test-key", base_url="https://example.local/")
    )
    try:
        assert client._build_url("/session") == "https://example.local/api/session"
        assert client._build_url("  session  ") == "https://example.local/api/session"
    finally:
        client.close()


def test_client_build_url_avoids_duplicate_api_when_base_url_already_has_api():
    client = Hyperbrowser(
        config=ClientConfig(api_key="test-key", base_url="https://example.local/api")
    )
    try:
        assert client._build_url("/session") == "https://example.local/api/session"
        assert client._build_url("/api/session") == "https://example.local/api/session"
        assert client._build_url("/api?foo=bar") == "https://example.local/api?foo=bar"
    finally:
        client.close()


def test_client_build_url_handles_nested_api_base_paths():
    client = Hyperbrowser(
        config=ClientConfig(
            api_key="test-key", base_url="https://example.local/custom/api"
        )
    )
    try:
        assert (
            client._build_url("/session") == "https://example.local/custom/api/session"
        )
        assert (
            client._build_url("/api/session")
            == "https://example.local/custom/api/session"
        )
    finally:
        client.close()


def test_client_build_url_reflects_runtime_base_url_changes():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        client.config.base_url = "https://example.local/api"
        assert client._build_url("/session") == "https://example.local/api/session"
    finally:
        client.close()


def test_client_build_url_rejects_runtime_invalid_base_url_changes():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        client.config.base_url = "invalid-base-url"
        with pytest.raises(HyperbrowserError, match="include a host"):
            client._build_url("/session")

        client.config.base_url = "https://example.local?foo=bar"
        with pytest.raises(
            HyperbrowserError, match="must not include query parameters"
        ):
            client._build_url("/session")

        client.config.base_url = "   "
        with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
            client._build_url("/session")

        client.config.base_url = 123  # type: ignore[assignment]
        with pytest.raises(HyperbrowserError, match="base_url must be a string"):
            client._build_url("/session")
    finally:
        client.close()


def test_client_build_url_rejects_empty_or_non_string_paths():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        with pytest.raises(HyperbrowserError, match="path must not be empty"):
            client._build_url("   ")
        with pytest.raises(HyperbrowserError, match="path must be a string"):
            client._build_url(123)  # type: ignore[arg-type]
        with pytest.raises(
            HyperbrowserError, match="path must not contain backslashes"
        ):
            client._build_url(r"\\session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain newline characters"
        ):
            client._build_url("/session\nnext")
        with pytest.raises(HyperbrowserError, match="path must be a relative API path"):
            client._build_url("https://api.hyperbrowser.ai/session")
        with pytest.raises(HyperbrowserError, match="path must be a relative API path"):
            client._build_url("mailto:ops@hyperbrowser.ai")
        with pytest.raises(HyperbrowserError, match="path must be a relative API path"):
            client._build_url("http:example.com")
        with pytest.raises(
            HyperbrowserError, match="path must not include URL fragments"
        ):
            client._build_url("/session#fragment")
    finally:
        client.close()


def test_client_build_url_allows_query_values_containing_absolute_urls():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        assert (
            client._build_url("/web/fetch?target=https://example.com")
            == "https://api.hyperbrowser.ai/api/web/fetch?target=https://example.com"
        )
        assert (
            client._build_url("/session?foo=bar")
            == "https://api.hyperbrowser.ai/api/session?foo=bar"
        )
    finally:
        client.close()


def test_client_build_url_normalizes_runtime_trailing_slashes():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        client.config.base_url = "https://example.local/"
        assert client._build_url("/session") == "https://example.local/api/session"

        client.config.base_url = "https://example.local/api/"
        assert client._build_url("/session") == "https://example.local/api/session"
    finally:
        client.close()
