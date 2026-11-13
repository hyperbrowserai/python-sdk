"""Exercise buffer inputs through the public sandbox file upload methods."""

import io
import struct
from array import array

import pytest

from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_files import (
    SandboxFilesApi as AsyncSandboxFilesApi,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_files import (
    SandboxFilesApi,
)


CASES = [
    (lambda: memoryview(b"\x00\xffab"), b"\x00\xffab"),
    (lambda: memoryview(b"prefixpayloadsuffix")[6:13], b"payload"),
    (lambda: memoryview(b"abcdef")[::2], b"ace"),
    (
        lambda: memoryview(array("H", [0x0102, 0x0304])),
        struct.pack("=HH", 0x0102, 0x0304),
    ),
    (lambda: memoryview(b""), b""),
    (lambda: b"abc", b"abc"),
    (lambda: bytearray(b"abc"), b"abc"),
    (lambda: io.BytesIO(b"abcdef"), b"abcdef"),
    (lambda: iter([b"ab", b"cd", b"ef"]), b"abcdef"),
]


class RecordingTransport:
    def request_json(self, path, *, content, params, method, headers):
        self.body = b"".join(content)
        self.path = path
        self.params = params
        self.method = method
        self.headers = headers
        return {"path": params["path"], "bytesWritten": len(self.body)}


class AsyncRecordingTransport(RecordingTransport):
    async def request_json(self, path, *, content, params, method, headers):
        chunks = [chunk async for chunk in content]
        return super().request_json(
            path,
            content=chunks,
            params=params,
            method=method,
            headers=headers,
        )


@pytest.mark.parametrize("make_stream,expected", CASES)
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.anyio
async def test_upload_stream_preserves_buffer_bytes(
    make_stream, expected, asynchronous
):
    stream = make_stream()
    if asynchronous:
        transport = AsyncRecordingTransport()
        files = AsyncSandboxFilesApi(transport, lambda: None)
        result = await files.upload_stream("/tmp/buffer.bin", stream, chunk_size=2)
    else:
        transport = RecordingTransport()
        files = SandboxFilesApi(transport, lambda: None)
        result = files.upload_stream("/tmp/buffer.bin", stream, chunk_size=2)

    assert transport.body == expected
    assert result.bytes_written == len(expected)
    assert result.path == "/tmp/buffer.bin"
    assert transport.path == "/sandbox/files/upload"
    assert transport.method == "PUT"
    assert transport.params == {"path": "/tmp/buffer.bin"}
    if isinstance(stream, memoryview):
        assert stream.tobytes() == expected  # The caller's view remains usable.
