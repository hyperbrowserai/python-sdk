import asyncio
from types import MappingProxyType

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


def test_sync_transport_accepts_custom_headers():
    transport = SyncTransport(
        api_key="test-key",
        headers={"X-Correlation-Id": "abc123", "User-Agent": "custom-agent"},
    )
    try:
        assert transport.client.headers["x-api-key"] == "test-key"
        assert transport.client.headers["X-Correlation-Id"] == "abc123"
        assert transport.client.headers["User-Agent"] == "custom-agent"
    finally:
        transport.close()


def test_async_transport_accepts_custom_headers():
    async def run() -> None:
        transport = AsyncTransport(
            api_key="test-key",
            headers={"X-Correlation-Id": "abc123", "User-Agent": "custom-agent"},
        )
        try:
            assert transport.client.headers["x-api-key"] == "test-key"
            assert transport.client.headers["X-Correlation-Id"] == "abc123"
            assert transport.client.headers["User-Agent"] == "custom-agent"
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_client_config_headers_are_applied_to_transport():
    client = Hyperbrowser(
        config=ClientConfig(api_key="test-key", headers={"X-Team-Trace": "team-1"})
    )
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "team-1"
    finally:
        client.close()


def test_sync_client_constructor_headers_are_applied_to_transport():
    headers = {"X-Team-Trace": "team-2"}
    client = Hyperbrowser(api_key="test-key", headers=headers)
    headers["X-Team-Trace"] = "mutated"
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "team-2"
    finally:
        client.close()


def test_async_client_config_headers_are_applied_to_transport():
    async def run() -> None:
        client = AsyncHyperbrowser(
            config=ClientConfig(api_key="test-key", headers={"X-Team-Trace": "team-1"})
        )
        try:
            assert client.transport.client.headers["X-Team-Trace"] == "team-1"
        finally:
            await client.close()

    asyncio.run(run())


def test_async_client_constructor_headers_are_applied_to_transport():
    async def run() -> None:
        headers = {"X-Team-Trace": "team-2"}
        client = AsyncHyperbrowser(api_key="test-key", headers=headers)
        headers["X-Team-Trace"] = "mutated"
        try:
            assert client.transport.client.headers["X-Team-Trace"] == "team-2"
        finally:
            await client.close()

    asyncio.run(run())


def test_sync_client_constructor_accepts_mapping_headers():
    source_headers = {"X-Team-Trace": "team-mapping-sync"}
    mapping_headers = MappingProxyType(source_headers)
    client = Hyperbrowser(api_key="test-key", headers=mapping_headers)
    source_headers["X-Team-Trace"] = "mutated"
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "team-mapping-sync"
    finally:
        client.close()


def test_async_client_constructor_accepts_mapping_headers():
    async def run() -> None:
        source_headers = {"X-Team-Trace": "team-mapping-async"}
        mapping_headers = MappingProxyType(source_headers)
        client = AsyncHyperbrowser(api_key="test-key", headers=mapping_headers)
        source_headers["X-Team-Trace"] = "mutated"
        try:
            assert (
                client.transport.client.headers["X-Team-Trace"] == "team-mapping-async"
            )
        finally:
            await client.close()

    asyncio.run(run())


def test_sync_client_constructor_reads_headers_from_environment(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Team-Trace":"env-sync"}')
    client = Hyperbrowser(api_key="test-key")
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "env-sync"
    finally:
        client.close()


def test_async_client_constructor_reads_headers_from_environment(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Team-Trace":"env-async"}')

    async def run() -> None:
        client = AsyncHyperbrowser(api_key="test-key")
        try:
            assert client.transport.client.headers["X-Team-Trace"] == "env-async"
        finally:
            await client.close()

    asyncio.run(run())


def test_client_constructor_rejects_invalid_env_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_HEADERS"):
        Hyperbrowser(api_key="test-key")


def test_client_constructor_rejects_mixed_config_and_direct_args():
    with pytest.raises(TypeError, match="Pass either `config`"):
        Hyperbrowser(
            config=ClientConfig(api_key="test-key"),
            headers={"X-Team-Trace": "team-1"},
        )


def test_async_client_constructor_rejects_mixed_config_and_direct_args():
    with pytest.raises(TypeError, match="Pass either `config`"):
        AsyncHyperbrowser(
            config=ClientConfig(api_key="test-key"),
            headers={"X-Team-Trace": "team-1"},
        )
