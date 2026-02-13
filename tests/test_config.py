import pytest

from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError


def test_client_config_from_env_raises_hyperbrowser_error_without_api_key(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_raises_hyperbrowser_error_for_blank_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "   ")

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_API_KEY"):
        ClientConfig.from_env()


def test_client_config_from_env_reads_api_key_and_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "https://example.local")

    config = ClientConfig.from_env()

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"


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


def test_client_config_normalizes_whitespace_and_trailing_slash():
    config = ClientConfig(api_key="  test-key  ", base_url=" https://example.local/ ")

    assert config.api_key == "test-key"
    assert config.base_url == "https://example.local"


def test_client_config_rejects_non_string_values():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        ClientConfig(api_key=None)  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="base_url must be a string"):
        ClientConfig(api_key="test-key", base_url=None)  # type: ignore[arg-type]


def test_client_config_rejects_empty_or_invalid_base_url():
    with pytest.raises(HyperbrowserError, match="base_url must not be empty"):
        ClientConfig(api_key="test-key", base_url="   ")

    with pytest.raises(HyperbrowserError, match="base_url must start with"):
        ClientConfig(api_key="test-key", base_url="api.hyperbrowser.ai")
