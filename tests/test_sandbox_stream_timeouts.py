"""Exercise stream deadlines with real sockets, including HTTPX body reads."""

import json
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import anyio
import httpx
import pytest

from hyperbrowser.client.managers.async_manager.sandboxes import (
    sandbox_transport as async_transport,
)
from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as AsyncProcesses,
)
from hyperbrowser.client.managers.sync_manager.sandboxes import (
    sandbox_transport as sync_transport,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as SyncProcesses,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.sandbox_common import RuntimeConnection


@pytest.fixture
def stream_server():
    servers = []

    def start(respond):
        stopped = threading.Event()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append((self.command, self.headers.get("Authorization")))
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                try:
                    respond(self, stopped)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # Expected when a timeout closes the client socket.

            do_POST = do_GET

            def headers_for(self, status=200, content_type="text/event-stream"):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.end_headers()

            def event(self, name, data):
                self.wfile.write(
                    ("event: " + name + "\ndata: " + json.dumps(data) + "\n\n").encode()
                )
                self.wfile.flush()

            def started(self):
                self.headers_for()
                self.event(
                    "started",
                    {
                        "id": "p1",
                        "status": "running",
                        "command": "quiet",
                        "cwd": "/tmp",
                        "started_at": 1,
                    },
                )

            def finished(self):
                self.event(
                    "output",
                    {
                        "seq": 1,
                        "stream": "stdout",
                        "data": "finished",
                        "timestamp": 2,
                    },
                )
                self.event(
                    "done",
                    {
                        "id": "p1",
                        "status": "exited",
                        "exit_code": 0,
                        "started_at": 1,
                        "completed_at": 2,
                        "last_seq": 1,
                    },
                )

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(
            target=partial(server.serve_forever, poll_interval=0.02), daemon=True
        )
        thread.start()
        servers.append((server, thread, stopped))
        return SimpleNamespace(
            url="http://127.0.0.1:{}".format(server.server_port), requests=requests
        )

    yield start
    for server, thread, stopped in servers:
        stopped.set()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture(params=["sync", "async"])
def client(request, monkeypatch):
    asynchronous = request.param == "async"
    module = async_transport if asynchronous else sync_transport

    async def call(function, *args, **kwargs):
        if asynchronous:
            return await function(*args, **kwargs)
        return await anyio.to_thread.run_sync(partial(function, *args, **kwargs))

    def create(server, request_timeout, idle_timeout):
        monkeypatch.setattr(module, "PROCESS_STREAM_IDLE_TIMEOUT_SECONDS", idle_timeout)
        refreshes = []

        def resolve(refresh):
            refreshes.append(refresh)
            return RuntimeConnection(
                sandbox_id="test",
                base_url=server.url,
                token="fresh" if refresh else "old",
            )

        async def async_resolve(refresh):
            return resolve(refresh)

        transport = module.RuntimeTransport(
            async_resolve if asynchronous else resolve, timeout=request_timeout
        )
        api = (AsyncProcesses if asynchronous else SyncProcesses)(transport)
        return SimpleNamespace(
            api=api, transport=transport, call=call, refreshes=refreshes
        )

    return create


@pytest.mark.anyio
async def test_process_stream_accepts_line_terminators(
    stream_server, client, monkeypatch
):
    # HTTPX 0.23, our minimum supported version, keeps the newline on each line.
    iter_lines = httpx.Response.iter_lines
    aiter_lines = httpx.Response.aiter_lines

    def legacy_lines(response):
        for line in iter_lines(response):
            yield line + "\n"

    async def async_legacy_lines(response):
        async for line in aiter_lines(response):
            yield line + "\n"

    monkeypatch.setattr(httpx.Response, "iter_lines", legacy_lines)
    monkeypatch.setattr(httpx.Response, "aiter_lines", async_legacy_lines)

    def respond(handler, stopped):
        handler.started()
        handler.finished()

    c = client(stream_server(respond), request_timeout=1, idle_timeout=1)
    handle = await c.call(c.api.start, "quiet")
    try:
        result = await c.call(handle.wait, timeout_sec=3)
        assert (result.stdout, result.exit_code) == ("finished", 0)
    finally:
        await c.call(handle.disconnect)


@pytest.mark.anyio
@pytest.mark.parametrize("refresh", [False, True])
async def test_quiet_process_and_heartbeats_outlive_request_timeout(
    stream_server, client, refresh
):
    def respond(handler, stopped):
        if refresh and handler.headers["Authorization"] == "Bearer old":
            handler.headers_for(401, "application/json")
            handler.wfile.write(b'{"error":"expired"}')
            return
        handler.started()
        # Longer than the ordinary request timeout, shorter than stream idle.
        if stopped.wait(0.6):
            return
        # Total duration exceeds stream idle too: each heartbeat resets it.
        for _ in range(4):
            handler.event("keepalive", {})
            if stopped.wait(0.25):
                return
        handler.finished()

    server = stream_server(respond)
    c = client(server, request_timeout=0.25, idle_timeout=1.0)
    handle = await c.call(c.api.start, "quiet")
    try:
        result = await c.call(handle.wait, timeout_sec=5)
        assert (result.stdout, result.exit_code) == ("finished", 0)
        assert c.refreshes == ([False, True] if refresh else [False])
        assert len(server.requests) == (2 if refresh else 1)
    finally:
        await c.call(handle.disconnect)


@pytest.mark.anyio
async def test_missing_heartbeats_fail_without_reexecuting(stream_server, client):
    def respond(handler, stopped):
        handler.started()
        stopped.wait(10)

    server = stream_server(respond)
    c = client(server, request_timeout=5, idle_timeout=0.25)
    handle = await c.call(c.api.start, "quiet")
    try:
        with pytest.raises(HyperbrowserError) as exc:
            await c.call(handle.wait, timeout_sec=2)
        assert exc.value.code == "incomplete_output"
        assert exc.value.details["process_id"] == "p1"
        assert not exc.value.retryable
        assert len(server.requests) == 1
    finally:
        await c.call(handle.disconnect)


@pytest.mark.anyio
async def test_response_headers_keep_ordinary_request_timeout(stream_server, client):
    def respond(handler, stopped):
        stopped.wait(2)

    server = stream_server(respond)
    c = client(server, request_timeout=0.25, idle_timeout=5)
    with pytest.raises(HyperbrowserError) as exc:
        await c.call(c.api.start, "quiet")
    assert isinstance(exc.value.original_error, httpx.ReadTimeout)
    assert len(server.requests) == 1


@pytest.mark.anyio
async def test_json_body_keeps_ordinary_request_timeout(stream_server, client):
    def respond(handler, stopped):
        handler.headers_for(200, "application/json")
        stopped.wait(2)

    server = stream_server(respond)
    c = client(server, request_timeout=0.25, idle_timeout=5)
    with pytest.raises(HyperbrowserError) as exc:
        await c.call(c.transport.request_json, "/sandbox/processes/p1")
    assert isinstance(exc.value.original_error, httpx.ReadTimeout)
    assert len(server.requests) == 1
