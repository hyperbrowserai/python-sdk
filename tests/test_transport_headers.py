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


def test_sync_transport_case_insensitive_header_overrides_replace_defaults():
    transport = SyncTransport(
        api_key="test-key",
        headers={"user-agent": "custom-agent", "X-API-KEY": "override-key"},
    )
    try:
        user_agent_values = [
            value
            for key, value in transport.client.headers.multi_items()
            if key.lower() == "user-agent"
        ]
        api_key_values = [
            value
            for key, value in transport.client.headers.multi_items()
            if key.lower() == "x-api-key"
        ]
        assert user_agent_values == ["custom-agent"]
        assert api_key_values == ["override-key"]
    finally:
        transport.close()


def test_async_transport_case_insensitive_header_overrides_replace_defaults():
    async def run() -> None:
        transport = AsyncTransport(
            api_key="test-key",
            headers={"user-agent": "custom-agent", "X-API-KEY": "override-key"},
        )
        try:
            user_agent_values = [
                value
                for key, value in transport.client.headers.multi_items()
                if key.lower() == "user-agent"
            ]
            api_key_values = [
                value
                for key, value in transport.client.headers.multi_items()
                if key.lower() == "x-api-key"
            ]
            assert user_agent_values == ["custom-agent"]
            assert api_key_values == ["override-key"]
        finally:
            await transport.close()

    asyncio.run(run())
