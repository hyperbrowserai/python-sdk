from types import SimpleNamespace

import httpx
import pytest

import hyperbrowser.client.managers.async_manager.sandbox as async_sandbox_module
import hyperbrowser.client.managers.sync_manager.sandbox as sync_sandbox_module
import hyperbrowser.transport.async_transport as async_transport_module
import hyperbrowser.transport.sync as sync_transport_module
from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxManager as AsyncSandboxManager,
)
from hyperbrowser.client.managers.sync_manager.sandbox import SandboxManager
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


def make_response(status_code, payload=None, text=None):
    request = httpx.Request("GET", "https://api.hyperbrowser.ai/api/test")
    if payload is not None:
        return httpx.Response(status_code, json=payload, request=request)
    return httpx.Response(status_code, text=text or "", request=request)


class SequencedSyncClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def _next(self, method):
        self.calls.append(method)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def get(self, url, **kwargs):
        return self._next("GET")

    def post(self, url, **kwargs):
        return self._next("POST")

    def request(self, method, url, **kwargs):
        return self._next(method)


class SequencedAsyncClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def _next(self, method):
        self.calls.append(method)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def get(self, url, **kwargs):
        return self._next("GET")

    async def post(self, url, **kwargs):
        return self._next("POST")

    async def request(self, method, url, **kwargs):
        return self._next(method)


def make_sync_transport(client):
    transport = object.__new__(SyncTransport)
    transport.client = client
    return transport


def make_async_transport(client):
    transport = object.__new__(AsyncTransport)
    transport.client = client
    transport._closed = True
    return transport


def make_sync_sandbox_manager(client):
    manager = object.__new__(SandboxManager)
    manager._client = SimpleNamespace(
        transport=SimpleNamespace(client=client),
        _build_url=lambda path: f"https://api.hyperbrowser.ai/api{path}",
    )
    return manager


def make_async_sandbox_manager(client):
    manager = object.__new__(AsyncSandboxManager)
    manager._client = SimpleNamespace(
        transport=SimpleNamespace(client=client),
        _build_url=lambda path: f"https://api.hyperbrowser.ai/api{path}",
    )
    return manager


def test_sync_transport_get_retries_transient_status(monkeypatch):
    client = SequencedSyncClient(
        [make_response(502, text="Bad Gateway"), make_response(200, {"ok": True})]
    )
    delays = []
    monkeypatch.setattr(sync_transport_module.time, "sleep", delays.append)

    result = make_sync_transport(client).get("https://example.test")

    assert result.data == {"ok": True}
    assert client.calls == ["GET", "GET"]
    assert len(delays) == 1


def test_sync_transport_get_stops_after_three_attempts(monkeypatch):
    client = SequencedSyncClient([make_response(503)] * 3)
    monkeypatch.setattr(sync_transport_module.time, "sleep", lambda _: None)

    with pytest.raises(HyperbrowserError) as exc_info:
        make_sync_transport(client).get("https://example.test")

    assert exc_info.value.status_code == 503
    assert exc_info.value.retryable is True
    assert client.calls == ["GET", "GET", "GET"]


def test_sync_transport_post_does_not_retry(monkeypatch):
    client = SequencedSyncClient(
        [make_response(502, text="Bad Gateway"), make_response(200, {"ok": True})]
    )
    delays = []
    monkeypatch.setattr(sync_transport_module.time, "sleep", delays.append)

    with pytest.raises(HyperbrowserError) as exc_info:
        make_sync_transport(client).post("https://example.test", {"value": 1})

    assert exc_info.value.status_code == 502
    assert exc_info.value.retryable is True
    assert client.calls == ["POST"]
    assert delays == []


@pytest.mark.anyio
async def test_async_transport_get_retries_transient_network_error(monkeypatch):
    request = httpx.Request("GET", "https://example.test")
    client = SequencedAsyncClient(
        [httpx.ReadTimeout("", request=request), make_response(200, {"ok": True})]
    )
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(async_transport_module.asyncio, "sleep", record_sleep)

    result = await make_async_transport(client).get("https://example.test")

    assert result.data == {"ok": True}
    assert client.calls == ["GET", "GET"]
    assert len(delays) == 1


def test_sync_sandbox_get_retries_transient_status(monkeypatch):
    client = SequencedSyncClient(
        [make_response(502, text="Bad Gateway"), make_response(200, {"ok": True})]
    )
    delays = []
    monkeypatch.setattr(sync_sandbox_module.time, "sleep", delays.append)

    result = make_sync_sandbox_manager(client)._request("GET", "/sandbox/test")

    assert result == {"ok": True}
    assert client.calls == ["GET", "GET"]
    assert len(delays) == 1


@pytest.mark.anyio
async def test_async_sandbox_get_retries_transient_status(monkeypatch):
    client = SequencedAsyncClient(
        [make_response(504, text="Gateway Timeout"), make_response(200, {"ok": True})]
    )
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(async_sandbox_module.asyncio, "sleep", record_sleep)

    result = await make_async_sandbox_manager(client)._request("GET", "/sandbox/test")

    assert result == {"ok": True}
    assert client.calls == ["GET", "GET"]
    assert len(delays) == 1


@pytest.mark.anyio
async def test_async_sandbox_post_does_not_retry(monkeypatch):
    client = SequencedAsyncClient(
        [make_response(502, text="Bad Gateway"), make_response(200, {"ok": True})]
    )
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(async_sandbox_module.asyncio, "sleep", record_sleep)

    with pytest.raises(HyperbrowserError) as exc_info:
        await make_async_sandbox_manager(client)._request(
            "POST", "/sandbox", data={"image": "test"}
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.retryable is True
    assert client.calls == ["POST"]
    assert delays == []
