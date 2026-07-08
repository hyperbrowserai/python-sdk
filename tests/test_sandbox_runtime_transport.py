import httpx
import pytest

from hyperbrowser.client.managers.async_manager.sandboxes import (
    sandbox_transport as async_transport_module,
)
from hyperbrowser.client.managers.sync_manager.sandboxes import (
    sandbox_transport as sync_transport_module,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.sandbox_common import RuntimeConnection


def _connection(token: str) -> RuntimeConnection:
    return RuntimeConnection(
        sandbox_id="sbx_123",
        base_url="https://runtime.example.com/sandbox/sbx_123",
        token=token,
    )


def test_sync_runtime_transport_does_not_retry_consumed_stream_body(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def request(self, method, url, headers, json, content):
            body = b"".join(content)
            calls.append({"headers": headers, "body": body})
            return httpx.Response(
                401,
                request=httpx.Request(method, url),
            )

        def close(self):
            pass

    refresh_flags = []

    def resolve_connection(force_refresh):
        refresh_flags.append(force_refresh)
        return _connection("fresh-token" if force_refresh else "old-token")

    monkeypatch.setattr(sync_transport_module.httpx, "Client", FakeClient)
    transport = sync_transport_module.RuntimeTransport(resolve_connection)

    with pytest.raises(HyperbrowserError) as exc_info:
        transport.request_json(
            "/sandbox/files/upload",
            method="PUT",
            content=(chunk for chunk in [b"payload"]),
        )

    assert exc_info.value.status_code == 401
    assert refresh_flags == [False]
    assert calls == [
        {
            "headers": {"Authorization": "Bearer old-token"},
            "body": b"payload",
        }
    ]


@pytest.mark.anyio
async def test_async_runtime_transport_does_not_retry_consumed_stream_body(
    monkeypatch,
):
    calls = []

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def request(self, method, url, headers, json, content):
            chunks = []
            async for chunk in content:
                chunks.append(chunk)
            calls.append({"headers": headers, "body": b"".join(chunks)})
            return httpx.Response(
                401,
                request=httpx.Request(method, url),
            )

        async def aclose(self):
            pass

    async def stream_body():
        yield b"payload"

    refresh_flags = []

    async def resolve_connection(force_refresh):
        refresh_flags.append(force_refresh)
        return _connection("fresh-token" if force_refresh else "old-token")

    monkeypatch.setattr(async_transport_module.httpx, "AsyncClient", FakeAsyncClient)
    transport = async_transport_module.RuntimeTransport(resolve_connection)

    with pytest.raises(HyperbrowserError) as exc_info:
        await transport.request_json(
            "/sandbox/files/upload",
            method="PUT",
            content=stream_body(),
        )

    assert exc_info.value.status_code == 401
    assert refresh_flags == [False]
    assert calls == [
        {
            "headers": {"Authorization": "Bearer old-token"},
            "body": b"payload",
        }
    ]
