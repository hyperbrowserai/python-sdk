from hyperbrowser import Hyperbrowser
from hyperbrowser.config import ClientConfig


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
    finally:
        client.close()


def test_client_build_url_uses_normalized_base_url():
    client = Hyperbrowser(
        config=ClientConfig(api_key="test-key", base_url="https://example.local/")
    )
    try:
        assert client._build_url("/session") == "https://example.local/api/session"
    finally:
        client.close()
