import asyncio

from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport
from hyperbrowser.version import __version__


def test_sync_transport_sets_default_sdk_headers():
    transport = SyncTransport(api_key="test-key")
    try:
        assert transport.client.headers["x-api-key"] == "test-key"
        assert (
            transport.client.headers["User-Agent"]
            == f"hyperbrowser-python-sdk/{__version__}"
        )
    finally:
        transport.close()


def test_async_transport_sets_default_sdk_headers():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            assert transport.client.headers["x-api-key"] == "test-key"
            assert (
                transport.client.headers["User-Agent"]
                == f"hyperbrowser-python-sdk/{__version__}"
            )
        finally:
            await transport.close()

    asyncio.run(run())
