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
