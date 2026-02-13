import asyncio

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.config import ClientConfig
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
