import asyncio

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserError


def test_sync_client_rejects_negative_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be non-negative"):
        Hyperbrowser(api_key="test-key", timeout=-1)


def test_async_client_rejects_negative_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be non-negative"):
        AsyncHyperbrowser(api_key="test-key", timeout=-1)


def test_sync_client_accepts_none_timeout():
    client = Hyperbrowser(api_key="test-key", timeout=None)
    client.close()


def test_async_client_accepts_none_timeout():
    async def run() -> None:
        client = AsyncHyperbrowser(api_key="test-key", timeout=None)
        await client.close()

    asyncio.run(run())
