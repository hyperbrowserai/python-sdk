import asyncio

import pytest

from hyperbrowser.client.async_client import AsyncHyperbrowser
from hyperbrowser.client.managers.async_manager.session import SessionEventLogsManager
from hyperbrowser.client.sync import Hyperbrowser
from hyperbrowser.models.session import SessionEventLogListResponse


def test_sync_client_supports_context_manager():
    client = Hyperbrowser(api_key="test-key")
    close_calls = {"count": 0}
    original_close = client.transport.close

    def tracked_close() -> None:
        close_calls["count"] += 1
        original_close()

    client.transport.close = tracked_close

    with client as entered:
        assert entered is client

    assert close_calls["count"] == 1


def test_async_client_supports_context_manager():
    async def run() -> None:
        client = AsyncHyperbrowser(api_key="test-key")
        close_calls = {"count": 0}
        original_close = client.transport.close

        async def tracked_close() -> None:
            close_calls["count"] += 1
            await original_close()

        client.transport.close = tracked_close

        async with client as entered:
            assert entered is client

        assert close_calls["count"] == 1

    asyncio.run(run())


def test_sync_client_context_manager_closes_transport_on_exception():
    client = Hyperbrowser(api_key="test-key")
    close_calls = {"count": 0}
    original_close = client.transport.close

    def tracked_close() -> None:
        close_calls["count"] += 1
        original_close()

    client.transport.close = tracked_close

    with pytest.raises(RuntimeError, match="sync boom"):
        with client:
            raise RuntimeError("sync boom")

    assert close_calls["count"] == 1


def test_async_client_context_manager_closes_transport_on_exception():
    async def run() -> None:
        client = AsyncHyperbrowser(api_key="test-key")
        close_calls = {"count": 0}
        original_close = client.transport.close

        async def tracked_close() -> None:
            close_calls["count"] += 1
            await original_close()

        client.transport.close = tracked_close

        with pytest.raises(RuntimeError, match="async boom"):
            async with client:
                raise RuntimeError("async boom")

        assert close_calls["count"] == 1

    asyncio.run(run())


def test_async_session_event_logs_annotation_is_response_model():
    assert (
        SessionEventLogsManager.list.__annotations__["return"]
        is SessionEventLogListResponse
    )
