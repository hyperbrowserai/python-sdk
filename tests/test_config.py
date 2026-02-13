import pytest

from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError


def test_client_config_from_env_raises_hyperbrowser_error_without_api_key(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_reads_api_key_and_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://example.local")

    config = ClientConfig.from_env()

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"
