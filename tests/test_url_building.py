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


def test_client_build_url_rejects_empty_or_non_string_paths():
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        with pytest.raises(HyperbrowserError, match="path must not be empty"):
            client._build_url("   ")
        with pytest.raises(HyperbrowserError, match="path must be a string"):
            client._build_url(123)  # type: ignore[arg-type]
        with pytest.raises(HyperbrowserError, match="path must be a relative API path"):
            client._build_url("https://api.hyperbrowser.ai/session")
    finally:
        client.close()
