import asyncio
import base64
import threading

import pytest

from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as AsyncProcesses,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as SyncProcesses,
)
from hyperbrowser.exceptions import HyperbrowserError


def output(seq, data, stream="stdout"):
    return {
        "event": "output",
        "data": {
            "seq": seq,
            "stream": stream,
            "data": base64.b64encode(data).decode(),
            "encoding": "base64",
            "timestamp": 1,
        },
    }


def done(seq, **kwargs):
    return {
        "event": "done",
        "data": {
            "id": "p1",
            "status": "exited",
            "exit_code": 7,
            "started_at": 1,
            "completed_at": 2,
            "last_seq": seq,
            **kwargs,
        },
    }


STARTED = {
    "event": "started",
    "data": {
        "id": "p1",
        "status": "running",
        "command": "test",
        "cwd": "/tmp",
        "started_at": 1,
    },
}


class SyncTransport:
    def __init__(self, events):
        self.events = events
        self.calls = []
        self.closed = threading.Event()

    def stream_sse(self, path, **kwargs):
        self.calls.append((path, kwargs))
        kwargs["on_open"](self.closed.set)
        try:
            yield STARTED
            yield from self.events
        finally:
            self.closed.set()


class AsyncTransport:
    def __init__(self, events):
        self.events = events
        self.calls = []
        self.closed = False
        self.gate = None

    async def stream_sse(self, path, **kwargs):
        self.calls.append((path, kwargs))
        try:
            yield STARTED
            if self.gate is not None:
                await self.gate.wait()
            for event in self.events:
                yield event
        finally:
            self.closed = True


def large_output():
    # Exceeds the receiver's old 4 MiB replay limit and splits a UTF-8 character.
    chunk = b"x" * 32768
    events = [output(i + 1, chunk) for i in range(160)]
    events.extend(
        [
            output(161, b"\xe2"),
            output(162, b"\x82\xac"),
            output(163, b"error", "stderr"),
            done(163),
        ]
    )
    return events, "x" * (160 * len(chunk)) + "€"


def test_sync_collects_large_output_and_streams_from_same_request():
    events, expected = large_output()
    transport = SyncTransport(events)
    handle = SyncProcesses(transport).start("test")
    result = handle.wait(timeout_sec=5)
    assert (result.stdout, result.stderr, result.exit_code) == (expected, "error", 7)
    assert handle.status == "exited"
    streamed = list(handle.stream())
    assert "".join(e.data for e in streamed if e.type == "stdout") == expected
    assert streamed[-1].result == result
    handle.disconnect()
    assert transport.closed.wait(1)
    assert len(transport.calls) == 1
    assert transport.calls[0][1]["method"] == "POST"


@pytest.mark.anyio
async def test_async_collects_large_output_and_streams_from_same_request():
    events, expected = large_output()
    transport = AsyncTransport(events)
    handle = await AsyncProcesses(transport).start("test")
    streamed = [event async for event in handle.stream()]
    result = await handle.wait()
    assert (result.stdout, result.stderr, result.exit_code) == (expected, "error", 7)
    assert "".join(e.data for e in streamed if e.type == "stdout") == expected
    assert streamed[-1].result == result
    assert transport.closed
    assert len(transport.calls) == 1


FAILURES = [
    ([output(2, b"gap"), done(2)], 100, "incomplete_output"),
    ([output(1, b"no completion")], 100, "incomplete_output"),
    ([output(1, b"tail missing"), done(2)], 100, "incomplete_output"),
    ([done(0, output_truncated=True)], 100, "incomplete_output"),
    ([output(1, b"too much"), done(1)], 4, "output_limit_exceeded"),
]


@pytest.mark.parametrize("events,limit,code", FAILURES)
def test_sync_incomplete_output_is_not_success_or_reexecuted(events, limit, code):
    transport = SyncTransport(events)
    with pytest.raises(HyperbrowserError) as exc:
        SyncProcesses(transport).exec("test", max_output_bytes=limit)
    assert exc.value.code == code
    assert exc.value.details["process_id"] == "p1"
    assert not exc.value.retryable
    assert transport.closed.wait(1)
    assert len(transport.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("events,limit,code", FAILURES)
async def test_async_incomplete_output_is_not_success_or_reexecuted(
    events, limit, code
):
    transport = AsyncTransport(events)
    with pytest.raises(HyperbrowserError) as exc:
        await AsyncProcesses(transport).exec("test", max_output_bytes=limit)
    assert exc.value.code == code
    assert not exc.value.retryable
    assert transport.closed
    assert len(transport.calls) == 1


@pytest.mark.anyio
async def test_async_wait_timeout_keeps_collector_alive():
    transport = AsyncTransport([output(1, b"later"), done(1)])
    transport.gate = asyncio.Event()
    handle = await AsyncProcesses(transport).start("test")
    with pytest.raises(asyncio.TimeoutError):
        await handle.wait(timeout_ms=1)
    assert not transport.closed
    transport.gate.set()
    assert (await handle.wait()).stdout == "later"


@pytest.mark.anyio
@pytest.mark.parametrize("start_collector", [False, True])
async def test_async_disconnect_closes_stream_without_killing_command(start_collector):
    transport = AsyncTransport([])
    transport.gate = asyncio.Event()
    handle = await AsyncProcesses(transport).start("test")
    if start_collector:
        await asyncio.sleep(0)
    await handle.disconnect()
    assert transport.closed
    with pytest.raises(HyperbrowserError, match="disconnected"):
        await handle.wait()
    assert len(transport.calls) == 1


def test_sync_wait_timeout_and_disconnect_unblock_collector():
    transport = SyncTransport([])

    def events():
        assert transport.closed.wait(5)
        yield done(0)

    transport.events = events()
    handle = SyncProcesses(transport).start("test")
    with pytest.raises(TimeoutError):
        handle.wait(timeout_ms=1)
    handle.disconnect()
    handle._collector.join(1)
    assert not handle._collector.is_alive()
    with pytest.raises(HyperbrowserError, match="disconnected"):
        handle.wait()


@pytest.mark.anyio
async def test_async_exec_cancellation_closes_stream():
    transport = AsyncTransport([])
    transport.gate = asyncio.Event()
    task = asyncio.create_task(AsyncProcesses(transport).exec("test"))
    while not transport.calls:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert transport.closed


@pytest.mark.parametrize("limit", [0, -1, True, None])
def test_invalid_collection_limit_rejected_before_start(limit):
    transport = SyncTransport([])
    with pytest.raises(ValueError, match="positive integer"):
        SyncProcesses(transport).start("test", max_output_bytes=limit)
    assert not transport.calls
