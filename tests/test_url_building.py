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

        client.config.base_url = "https://example.local/\napi"
        with pytest.raises(
            HyperbrowserError, match="base_url must not contain newline characters"
        ):
            client._build_url("/session")

        client.config.base_url = "https://example .local"
        with pytest.raises(
            HyperbrowserError, match="base_url must not contain whitespace characters"
        ):
            client._build_url("/session")

        client.config.base_url = "https://example.local\\api"
        with pytest.raises(
            HyperbrowserError, match="base_url must not contain backslashes"
        ):
            client._build_url("/session")

        client.config.base_url = "https://example.local\x00api"
        with pytest.raises(
            HyperbrowserError, match="base_url must not contain control characters"
        ):
            client._build_url("/session")

        client.config.base_url = "https://example.local/%2e%2e/api"
        with pytest.raises(
            HyperbrowserError,
            match="base_url path must not contain relative path segments",
        ):
            client._build_url("/session")

        client.config.base_url = "https://user:pass@example.local"
        with pytest.raises(
            HyperbrowserError, match="base_url must not include user credentials"
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
        with pytest.raises(
            HyperbrowserError, match="path must not contain whitespace characters"
        ):
            client._build_url("/session name")
        with pytest.raises(
            HyperbrowserError, match="path must not contain control characters"
        ):
            client._build_url("/session\x00name")
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
        with pytest.raises(
            HyperbrowserError, match="path must not contain relative path segments"
        ):
            client._build_url("/../session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain relative path segments"
        ):
            client._build_url("/api/./session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain relative path segments"
        ):
            client._build_url("/%2e%2e/session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain relative path segments"
        ):
            client._build_url("/api/%2E/session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain relative path segments"
        ):
            client._build_url("/%252e%252e/session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain relative path segments"
        ):
            client._build_url("/%2525252e%2525252e/session")
        with pytest.raises(
            HyperbrowserError, match="path must not contain backslashes"
        ):
            client._build_url("/api/%5Csession")
        with pytest.raises(
            HyperbrowserError, match="path must not contain backslashes"
        ):
            client._build_url("/api/%255Csession")
        with pytest.raises(
            HyperbrowserError, match="path must not contain backslashes"
        ):
            client._build_url("/api/%2525255Csession")
        with pytest.raises(
            HyperbrowserError, match="path must not contain newline characters"
        ):
            client._build_url("/api/%0Asegment")
        with pytest.raises(
            HyperbrowserError, match="path must not contain newline characters"
        ):
            client._build_url("/api/%250Asegment")
        with pytest.raises(
            HyperbrowserError, match="path must not contain whitespace characters"
        ):
            client._build_url("/api/%20segment")
        with pytest.raises(
            HyperbrowserError, match="path must not contain whitespace characters"
        ):
            client._build_url("/api/%09segment")
        with pytest.raises(
            HyperbrowserError, match="path must not contain control characters"
        ):
            client._build_url("/api/%00segment")
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
