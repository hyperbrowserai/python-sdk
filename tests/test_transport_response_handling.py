import asyncio

import httpx
import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


def _build_response(status_code: int, body: str) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com/test")
    return httpx.Response(status_code, request=request, text=body)


class _RequestErrorResponse:
    def __init__(self, method: str, url: str) -> None:
        self._request = httpx.Request(method, url)

    def raise_for_status(self) -> None:
        raise httpx.RequestError("network down", request=self._request)


class _RequestErrorNoRequestResponse:
    def raise_for_status(self) -> None:
        raise httpx.RequestError("network down")


class _BrokenJsonSuccessResponse:
    status_code = 200
    content = b"{broken-json}"

    def raise_for_status(self) -> None:
        return None

    def json(self):
        raise RuntimeError("broken json")


class _BrokenJsonErrorResponse:
    status_code = 500
    content = b"{broken-json}"

    def raise_for_status(self) -> None:
        return None

    @property
    def text(self) -> str:
        raise RuntimeError("broken response text")

    def json(self):
        raise RuntimeError("broken json")


class _BrokenStatusCodeJsonResponse:
    content = b"{broken-json}"

    def raise_for_status(self) -> None:
        return None

    @property
    def status_code(self) -> int:
        raise RuntimeError("broken status code")

    def json(self):
        raise RuntimeError("broken json")


class _BooleanStatusNoContentResponse:
    status_code = True
    content = b""
    text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {}


class _BrokenStatusCodeHttpErrorResponse:
    content = b""
    text = "status error"

    def raise_for_status(self) -> None:
        request = httpx.Request("GET", "https://example.com/status-error")
        raise httpx.HTTPStatusError("status failure", request=request, response=self)

    @property
    def status_code(self) -> int:
        raise RuntimeError("broken status code")

    def json(self):
        return {"message": "status failure"}


def test_sync_handle_response_with_non_json_success_body_returns_status_only():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(200, "plain-text-response")

        api_response = transport._handle_response(response)

        assert api_response.status_code == 200
        assert api_response.data is None
    finally:
        transport.close()


def test_sync_handle_response_with_broken_json_success_payload_returns_status_only():
    transport = SyncTransport(api_key="test-key")
    try:
        api_response = transport._handle_response(
            _BrokenJsonSuccessResponse()  # type: ignore[arg-type]
        )

        assert api_response.status_code == 200
        assert api_response.data is None
    finally:
        transport.close()


def test_sync_handle_response_with_broken_json_error_payload_uses_default_message():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(HyperbrowserError, match="Unknown error occurred"):
            transport._handle_response(
                _BrokenJsonErrorResponse()  # type: ignore[arg-type]
            )
    finally:
        transport.close()


def test_sync_handle_response_with_broken_status_code_raises_hyperbrowser_error():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError, match="Failed to process response status code"
        ) as exc_info:
            transport._handle_response(
                _BrokenStatusCodeJsonResponse()  # type: ignore[arg-type]
            )
        assert exc_info.value.original_error is not None
    finally:
        transport.close()


def test_sync_handle_response_with_boolean_status_no_content_raises_hyperbrowser_error():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError, match="Failed to process response status code"
        ):
            transport._handle_response(
                _BooleanStatusNoContentResponse()  # type: ignore[arg-type]
            )
    finally:
        transport.close()


def test_sync_handle_response_with_http_status_error_and_broken_status_code():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError, match="Failed to process response status code"
        ):
            transport._handle_response(
                _BrokenStatusCodeHttpErrorResponse()  # type: ignore[arg-type]
            )
    finally:
        transport.close()


def test_sync_handle_response_with_request_error_includes_method_and_url():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError,
            match="Request GET https://example.com/network failed",
        ):
            transport._handle_response(
                _RequestErrorResponse("GET", "https://example.com/network")
            )
    finally:
        transport.close()


def test_sync_handle_response_with_request_error_normalizes_method_casing():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError,
            match="Request GET https://example.com/network failed",
        ):
            transport._handle_response(
                _RequestErrorResponse("get", "https://example.com/network")
            )
    finally:
        transport.close()


def test_sync_handle_response_with_request_error_normalizes_sentinel_method():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError,
            match="Request UNKNOWN https://example.com/network failed",
        ):
            transport._handle_response(
                _RequestErrorResponse("null", "https://example.com/network")
            )
    finally:
        transport.close()


def test_sync_handle_response_with_request_error_normalizes_numeric_like_method():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError,
            match="Request UNKNOWN https://example.com/network failed",
        ):
            transport._handle_response(
                _RequestErrorResponse("1e3", "https://example.com/network")
            )
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


def test_async_handle_response_with_broken_json_success_payload_returns_status_only():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            api_response = await transport._handle_response(
                _BrokenJsonSuccessResponse()  # type: ignore[arg-type]
            )

            assert api_response.status_code == 200
            assert api_response.data is None
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_broken_json_error_payload_uses_default_message():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(HyperbrowserError, match="Unknown error occurred"):
                await transport._handle_response(
                    _BrokenJsonErrorResponse()  # type: ignore[arg-type]
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_broken_status_code_raises_hyperbrowser_error():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError, match="Failed to process response status code"
            ) as exc_info:
                await transport._handle_response(
                    _BrokenStatusCodeJsonResponse()  # type: ignore[arg-type]
                )
            assert exc_info.value.original_error is not None
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_boolean_status_no_content_raises_hyperbrowser_error():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError, match="Failed to process response status code"
            ):
                await transport._handle_response(
                    _BooleanStatusNoContentResponse()  # type: ignore[arg-type]
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_http_status_error_and_broken_status_code():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError, match="Failed to process response status code"
            ):
                await transport._handle_response(
                    _BrokenStatusCodeHttpErrorResponse()  # type: ignore[arg-type]
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_request_error_includes_method_and_url():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request POST https://example.com/network failed",
            ):
                await transport._handle_response(
                    _RequestErrorResponse("POST", "https://example.com/network")
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_request_error_normalizes_method_casing():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request POST https://example.com/network failed",
            ):
                await transport._handle_response(
                    _RequestErrorResponse("post", "https://example.com/network")
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_request_error_normalizes_sentinel_method():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request UNKNOWN https://example.com/network failed",
            ):
                await transport._handle_response(
                    _RequestErrorResponse("undefined", "https://example.com/network")
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_handle_response_with_request_error_normalizes_numeric_like_method():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request UNKNOWN https://example.com/network failed",
            ):
                await transport._handle_response(
                    _RequestErrorResponse("1.5", "https://example.com/network")
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_handle_response_with_request_error_without_request_context():
    transport = SyncTransport(api_key="test-key")
    try:
        with pytest.raises(
            HyperbrowserError, match="Request UNKNOWN unknown URL failed"
        ):
            transport._handle_response(_RequestErrorNoRequestResponse())
    finally:
        transport.close()


def test_async_handle_response_with_request_error_without_request_context():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            with pytest.raises(
                HyperbrowserError, match="Request UNKNOWN unknown URL failed"
            ):
                await transport._handle_response(_RequestErrorNoRequestResponse())
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


def test_sync_handle_response_with_dict_without_message_keys_stringifies_payload():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(500, '{"code":"UPSTREAM_FAILURE","retryable":false}')

        with pytest.raises(HyperbrowserError, match='"code": "UPSTREAM_FAILURE"'):
            transport._handle_response(response)
    finally:
        transport.close()


def test_async_handle_response_with_non_dict_json_uses_first_item_payload():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        try:
            response = _build_response(500, '[{"code":"UPSTREAM_FAILURE"}]')

            with pytest.raises(HyperbrowserError, match='"code": "UPSTREAM_FAILURE"'):
                await transport._handle_response(response)
        finally:
            await transport.close()

    asyncio.run(run())


def test_sync_handle_response_with_validation_error_detail_list_uses_msg_values():
    transport = SyncTransport(api_key="test-key")
    try:
        response = _build_response(
            422,
            '{"detail":[{"msg":"field required"},{"msg":"invalid email address"}]}',
        )

        with pytest.raises(
            HyperbrowserError, match="field required; invalid email address"
        ):
            transport._handle_response(response)
    finally:
        transport.close()


def test_sync_transport_post_wraps_request_errors_with_url_context():
    transport = SyncTransport(api_key="test-key")
    original_post = transport.client.post

    def failing_post(*args, **kwargs):
        request = httpx.Request("POST", "https://example.com/post")
        raise httpx.RequestError("network down", request=request)

    transport.client.post = failing_post  # type: ignore[assignment]
    try:
        with pytest.raises(
            HyperbrowserError, match="Request POST https://example.com/post failed"
        ):
            transport.post("https://example.com/post", data={"ok": True})
    finally:
        transport.client.post = original_post  # type: ignore[assignment]
        transport.close()


def test_sync_transport_post_wraps_unexpected_errors_with_url_context():
    transport = SyncTransport(api_key="test-key")
    original_post = transport.client.post

    def failing_post(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.post = failing_post  # type: ignore[assignment]
    try:
        with pytest.raises(
            HyperbrowserError, match="Request POST https://example.com/post failed"
        ):
            transport.post("https://example.com/post", data={"ok": True})
    finally:
        transport.client.post = original_post  # type: ignore[assignment]
        transport.close()


def test_async_transport_get_wraps_request_errors_with_url_context():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_get = transport.client.get

        async def failing_get(*args, **kwargs):
            request = httpx.Request("GET", "https://example.com/get")
            raise httpx.RequestError("network down", request=request)

        transport.client.get = failing_get  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request GET https://example.com/get failed",
            ):
                await transport.get("https://example.com/get")
        finally:
            transport.client.get = original_get  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_sync_transport_delete_wraps_unexpected_errors_with_url_context():
    transport = SyncTransport(api_key="test-key")
    original_delete = transport.client.delete

    def failing_delete(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.delete = failing_delete  # type: ignore[assignment]
    try:
        with pytest.raises(
            HyperbrowserError,
            match="Request DELETE https://example.com/delete failed",
        ):
            transport.delete("https://example.com/delete")
    finally:
        transport.client.delete = original_delete  # type: ignore[assignment]
        transport.close()


def test_sync_transport_wraps_unexpected_errors_with_invalid_url_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get(None)  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_wraps_unexpected_errors_with_numeric_url_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get(123)  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_wraps_unexpected_errors_with_boolean_url_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get(True)  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_wraps_unexpected_errors_with_sentinel_url_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get("null")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_wraps_unexpected_errors_with_boolean_string_url_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get("true")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_wraps_unexpected_errors_with_numeric_like_string_url_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise RuntimeError("boom")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get("1.5")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_async_transport_put_wraps_unexpected_errors_with_url_context():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request PUT https://example.com/put failed",
            ):
                await transport.put("https://example.com/put", data={"ok": True})
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_wraps_unexpected_errors_with_invalid_url_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request PUT unknown URL failed"
            ):
                await transport.put(None)  # type: ignore[arg-type]
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_wraps_unexpected_errors_with_numeric_url_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request PUT unknown URL failed"
            ):
                await transport.put(123)  # type: ignore[arg-type]
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_wraps_unexpected_errors_with_boolean_url_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request PUT unknown URL failed"
            ):
                await transport.put(False)  # type: ignore[arg-type]
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_wraps_unexpected_errors_with_sentinel_url_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request PUT unknown URL failed"
            ):
                await transport.put("none")
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_wraps_unexpected_errors_with_boolean_string_url_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request PUT unknown URL failed"
            ):
                await transport.put("false")
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_wraps_unexpected_errors_with_numeric_like_string_url_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_put = transport.client.put

        async def failing_put(*args, **kwargs):
            raise RuntimeError("boom")

        transport.client.put = failing_put  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request PUT unknown URL failed"
            ):
                await transport.put("1e6")
        finally:
            transport.client.put = original_put  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_sync_transport_request_error_without_request_uses_fallback_url():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(
            HyperbrowserError, match="Request GET https://example.com/fallback failed"
        ):
            transport.get("https://example.com/fallback")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_url_like_fallback():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(
            HyperbrowserError, match="Request GET https://example.com/fallback failed"
        ):
            transport.get(httpx.URL("https://example.com/fallback"))  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_unknown_url_for_invalid_input():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get(None)  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_unknown_url_for_numeric_input():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get(123)  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_unknown_url_for_boolean_input():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get(False)  # type: ignore[arg-type]
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_unknown_url_for_sentinel_input():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get("undefined")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_unknown_url_for_boolean_string_input():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get("true")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_sync_transport_request_error_without_request_uses_unknown_url_for_numeric_like_string_input():
    transport = SyncTransport(api_key="test-key")
    original_get = transport.client.get

    def failing_get(*args, **kwargs):
        raise httpx.RequestError("network down")

    transport.client.get = failing_get  # type: ignore[assignment]
    try:
        with pytest.raises(HyperbrowserError, match="Request GET unknown URL failed"):
            transport.get("1.5")
    finally:
        transport.client.get = original_get  # type: ignore[assignment]
        transport.close()


def test_async_transport_request_error_without_request_uses_fallback_url():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request DELETE https://example.com/fallback failed",
            ):
                await transport.delete("https://example.com/fallback")
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_url_like_fallback():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError,
                match="Request DELETE https://example.com/fallback failed",
            ):
                await transport.delete(httpx.URL("https://example.com/fallback"))  # type: ignore[arg-type]
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_unknown_url_for_invalid_input():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request DELETE unknown URL failed"
            ):
                await transport.delete(None)  # type: ignore[arg-type]
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_unknown_url_for_numeric_input():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request DELETE unknown URL failed"
            ):
                await transport.delete(123)  # type: ignore[arg-type]
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_unknown_url_for_boolean_input():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request DELETE unknown URL failed"
            ):
                await transport.delete(True)  # type: ignore[arg-type]
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_unknown_url_for_sentinel_input():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request DELETE unknown URL failed"
            ):
                await transport.delete("nan")
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_unknown_url_for_boolean_string_input():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request DELETE unknown URL failed"
            ):
                await transport.delete("false")
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())


def test_async_transport_request_error_without_request_uses_unknown_url_for_numeric_like_string_input():
    async def run() -> None:
        transport = AsyncTransport(api_key="test-key")
        original_delete = transport.client.delete

        async def failing_delete(*args, **kwargs):
            raise httpx.RequestError("network down")

        transport.client.delete = failing_delete  # type: ignore[assignment]
        try:
            with pytest.raises(
                HyperbrowserError, match="Request DELETE unknown URL failed"
            ):
                await transport.delete("1e6")
        finally:
            transport.client.delete = original_delete  # type: ignore[assignment]
            await transport.close()

    asyncio.run(run())
