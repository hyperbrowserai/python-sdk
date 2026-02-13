import asyncio

import pytest

from hyperbrowser.transport.async_transport import AsyncTransport


class _FailingAsyncClient:
    async def aclose(self) -> None:
        raise RuntimeError("close failed")


class _TrackingAsyncClient:
    def __init__(self) -> None:
        self.close_calls = 0

    async def aclose(self) -> None:
        self.close_calls += 1


def test_async_transport_close_does_not_mark_closed_when_close_fails():
    transport = AsyncTransport(api_key="test-key")
    original_client = transport.client
    asyncio.run(original_client.aclose())
    transport.client = _FailingAsyncClient()  # type: ignore[assignment]

    async def run() -> None:
        with pytest.raises(RuntimeError, match="close failed"):
            await transport.close()

    asyncio.run(run())
    assert transport._closed is False


def test_async_transport_close_is_idempotent_after_success():
    transport = AsyncTransport(api_key="test-key")
    original_client = transport.client
    asyncio.run(original_client.aclose())
    tracking_client = _TrackingAsyncClient()
    transport.client = tracking_client  # type: ignore[assignment]

    async def run() -> None:
        await transport.close()
        await transport.close()

    asyncio.run(run())
    assert tracking_client.close_calls == 1
    assert transport._closed is True
