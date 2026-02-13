import asyncio

import httpx
import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


def _build_response(status_code: int, body: str) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com/test")
    return httpx.Response(status_code, request=request, text=body)


def test_sync_handle_response_with_non_json_success_body_returns_status_only():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(200, "plain-text-response")

        api_response = transport._handle_response(response)

        assert api_response.status_code == 200
        assert api_response.data is None
    finally:
        transport.close()


def test_async_handle_response_with_non_json_success_body_returns_status_only():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            response = _build_response(200, "plain-text-response")

            api_response = await transport._handle_response(response)

            assert api_response.status_code == 200
            assert api_response.data is None
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_handle_response_with_error_and_non_json_body_raises_hyperbrowser_error():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(500, "server exploded")

        with pytest.raises(HyperbrowserError, match="server exploded"):
            transport._handle_response(response)
    finally:
        transport.close()


def test_async_handle_response_with_error_and_non_json_body_raises_hyperbrowser_error():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            response = _build_response(500, "server exploded")

            with pytest.raises(HyperbrowserError, match="server exploded"):
                await transport._handle_response(response)
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_handle_response_with_json_string_error_body_uses_string_message():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(500, '"upstream failed"')

        with pytest.raises(HyperbrowserError, match="upstream failed"):
            transport._handle_response(response)
    finally:
        transport.close()


def test_async_handle_response_with_json_string_error_body_uses_string_message():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            response = _build_response(500, '"upstream failed"')

            with pytest.raises(HyperbrowserError, match="upstream failed"):
                await transport._handle_response(response)
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_handle_response_with_non_string_message_field_coerces_to_string():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(500, '{"message":{"detail":"failed"}}')

        with pytest.raises(HyperbrowserError, match="failed"):
            transport._handle_response(response)
    finally:
        transport.close()


def test_async_handle_response_with_non_string_message_field_coerces_to_string():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            response = _build_response(500, '{"message":{"detail":"failed"}}')

            with pytest.raises(HyperbrowserError, match="failed"):
                await transport._handle_response(response)
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_handle_response_with_nested_error_message_uses_nested_value():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(500, '{"error":{"message":"nested failure"}}')

        with pytest.raises(HyperbrowserError, match="nested failure"):
            transport._handle_response(response)
    finally:
        transport.close()


def test_async_handle_response_with_detail_field_uses_detail_value():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            response = _build_response(500, '{"detail":"invalid request"}')

            with pytest.raises(HyperbrowserError, match="invalid request"):
                await transport._handle_response(response)
        finally:
            await transport.close()

    asyncio.run(run())
