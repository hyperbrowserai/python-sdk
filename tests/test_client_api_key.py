import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserError


def test_sync_client_requires_api_key_when_not_in_env(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(
        HyperbrowserError,
        match="API key must be provided via `api_key` or HYPERBROWSER_API_KEY",
    ):
        Hyperbrowser()


def test_async_client_requires_api_key_when_not_in_env(monkeypatch):
    monkeypatch.delenv("HYPERBROWSER_API_KEY", raising=False)

    with pytest.raises(
        HyperbrowserError,
        match="API key must be provided via `api_key` or HYPERBROWSER_API_KEY",
    ):
        AsyncHyperbrowser()


def test_sync_client_rejects_blank_env_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "   ")

    with pytest.raises(
        HyperbrowserError,
        match="API key must be provided via `api_key` or HYPERBROWSER_API_KEY",
    ):
        Hyperbrowser()


def test_sync_client_rejects_blank_env_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "   ")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        Hyperbrowser()


def test_async_client_rejects_blank_env_base_url(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "test-key")
    monkeypatch.setenv("HYPERBROWSER_BASE_URL", "   ")

    with pytest.raises(
        HyperbrowserError, match="HYPERBROWSER_BASE_URL must not be empty"
    ):
        AsyncHyperbrowser()


def test_sync_client_rejects_non_string_api_key():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        Hyperbrowser(api_key=123)  # type: ignore[arg-type]


def test_async_client_rejects_non_string_api_key():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        AsyncHyperbrowser(api_key=123)  # type: ignore[arg-type]


def test_sync_client_rejects_blank_constructor_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")

    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        Hyperbrowser(api_key="   ")


def test_async_client_rejects_blank_constructor_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "env-key")

    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        AsyncHyperbrowser(api_key="\t")


def test_sync_client_rejects_control_character_api_key():
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        Hyperbrowser(api_key="bad\nkey")


def test_async_client_rejects_control_character_api_key():
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        AsyncHyperbrowser(api_key="bad\nkey")


def test_sync_client_rejects_control_character_env_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "bad\nkey")

    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        Hyperbrowser()


def test_async_client_rejects_control_character_env_api_key(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_API_KEY", "bad\nkey")

    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        AsyncHyperbrowser()
