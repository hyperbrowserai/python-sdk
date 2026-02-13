import asyncio
import io
from pathlib import Path
import pytest

from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
from hyperbrowser.exceptions import HyperbrowserError


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _SyncTransport:
    def __init__(self):
        self.received_file = None

    def post(self, url, data=None, files=None):
        assert url.endswith("/session/session_123/uploads")
        assert files is not None and "file" in files
        assert files["file"].closed is False
        self.received_file = files["file"]
        return _FakeResponse(
            {
                "message": "ok",
                "filePath": "/uploads/file.txt",
                "fileName": "file.txt",
                "originalName": "file.txt",
            }
        )


class _AsyncTransport:
    def __init__(self):
        self.received_file = None

    async def post(self, url, data=None, files=None):
        assert url.endswith("/session/session_123/uploads")
        assert files is not None and "file" in files
        assert files["file"].closed is False
        self.received_file = files["file"]
        return _FakeResponse(
            {
                "message": "ok",
                "filePath": "/uploads/file.txt",
                "fileName": "file.txt",
                "originalName": "file.txt",
            }
        )


class _FakeClient:
    def __init__(self, transport):
        self.transport = transport

    def _build_url(self, path: str) -> str:
        return f"https://api.hyperbrowser.ai/api{path}"


def _create_upload_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")
    return file_path


def test_sync_session_upload_file_accepts_pathlike(tmp_path):
    file_path = _create_upload_file(tmp_path)
    transport = _SyncTransport()
    manager = SyncSessionManager(_FakeClient(transport))

    response = manager.upload_file("session_123", file_path)

    assert response.file_name == "file.txt"
    assert (
        transport.received_file is not None and transport.received_file.closed is True
    )


def test_async_session_upload_file_accepts_pathlike(tmp_path):
    file_path = _create_upload_file(tmp_path)
    transport = _AsyncTransport()
    manager = AsyncSessionManager(_FakeClient(transport))

    async def run():
        return await manager.upload_file("session_123", file_path)

    response = asyncio.run(run())

    assert response.file_name == "file.txt"
    assert (
        transport.received_file is not None and transport.received_file.closed is True
    )


def test_sync_session_upload_file_accepts_file_like_object():
    transport = _SyncTransport()
    manager = SyncSessionManager(_FakeClient(transport))
    file_obj = io.BytesIO(b"content")

    response = manager.upload_file("session_123", file_obj)

    assert response.file_name == "file.txt"
    assert transport.received_file is file_obj


def test_async_session_upload_file_accepts_file_like_object():
    transport = _AsyncTransport()
    manager = AsyncSessionManager(_FakeClient(transport))
    file_obj = io.BytesIO(b"content")

    async def run():
        return await manager.upload_file("session_123", file_obj)

    response = asyncio.run(run())

    assert response.file_name == "file.txt"
    assert transport.received_file is file_obj


def test_sync_session_upload_file_rejects_invalid_input_type():
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))

    with pytest.raises(HyperbrowserError, match="file_input must be a file path"):
        manager.upload_file("session_123", 123)  # type: ignore[arg-type]


def test_async_session_upload_file_rejects_invalid_input_type():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))

    async def run():
        with pytest.raises(HyperbrowserError, match="file_input must be a file path"):
            await manager.upload_file("session_123", 123)  # type: ignore[arg-type]

    asyncio.run(run())


def test_sync_session_upload_file_rejects_non_callable_read_attribute():
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))
    fake_file = type("FakeFile", (), {"read": "not-callable"})()

    with pytest.raises(HyperbrowserError, match="file_input must be a file path"):
        manager.upload_file("session_123", fake_file)


def test_sync_session_upload_file_rejects_closed_file_like_object():
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))
    closed_file_obj = io.BytesIO(b"content")
    closed_file_obj.close()

    with pytest.raises(HyperbrowserError, match="file-like object must be open"):
        manager.upload_file("session_123", closed_file_obj)


def test_sync_session_upload_file_wraps_invalid_file_like_state_errors():
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))

    class _BrokenFileLike:
        @property
        def read(self):
            raise RuntimeError("broken read")

    with pytest.raises(HyperbrowserError, match="file-like object state is invalid"):
        manager.upload_file("session_123", _BrokenFileLike())


def test_sync_session_upload_file_preserves_hyperbrowser_read_state_errors():
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))

    class _BrokenFileLike:
        @property
        def read(self):
            raise HyperbrowserError("custom read state error")

    with pytest.raises(HyperbrowserError, match="custom read state error") as exc_info:
        manager.upload_file("session_123", _BrokenFileLike())

    assert exc_info.value.original_error is None


def test_sync_session_upload_file_preserves_hyperbrowser_closed_state_errors():
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))

    class _BrokenFileLike:
        def read(self):
            return b"content"

        @property
        def closed(self):
            raise HyperbrowserError("custom closed-state error")

    with pytest.raises(
        HyperbrowserError, match="custom closed-state error"
    ) as exc_info:
        manager.upload_file("session_123", _BrokenFileLike())

    assert exc_info.value.original_error is None


def test_async_session_upload_file_rejects_non_callable_read_attribute():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))
    fake_file = type("FakeFile", (), {"read": "not-callable"})()

    async def run():
        with pytest.raises(HyperbrowserError, match="file_input must be a file path"):
            await manager.upload_file("session_123", fake_file)

    asyncio.run(run())


def test_async_session_upload_file_rejects_closed_file_like_object():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))
    closed_file_obj = io.BytesIO(b"content")
    closed_file_obj.close()

    async def run():
        with pytest.raises(HyperbrowserError, match="file-like object must be open"):
            await manager.upload_file("session_123", closed_file_obj)

    asyncio.run(run())


def test_async_session_upload_file_wraps_invalid_file_like_state_errors():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))

    class _BrokenFileLike:
        @property
        def read(self):
            raise RuntimeError("broken read")

    async def run():
        with pytest.raises(
            HyperbrowserError, match="file-like object state is invalid"
        ):
            await manager.upload_file("session_123", _BrokenFileLike())

    asyncio.run(run())


def test_async_session_upload_file_preserves_hyperbrowser_read_state_errors():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))

    class _BrokenFileLike:
        @property
        def read(self):
            raise HyperbrowserError("custom read state error")

    async def run():
        with pytest.raises(
            HyperbrowserError, match="custom read state error"
        ) as exc_info:
            await manager.upload_file("session_123", _BrokenFileLike())
        assert exc_info.value.original_error is None

    asyncio.run(run())


def test_async_session_upload_file_preserves_hyperbrowser_closed_state_errors():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))

    class _BrokenFileLike:
        def read(self):
            return b"content"

        @property
        def closed(self):
            raise HyperbrowserError("custom closed-state error")

    async def run():
        with pytest.raises(
            HyperbrowserError, match="custom closed-state error"
        ) as exc_info:
            await manager.upload_file("session_123", _BrokenFileLike())
        assert exc_info.value.original_error is None

    asyncio.run(run())


def test_sync_session_upload_file_raises_hyperbrowser_error_for_missing_path(tmp_path):
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))
    missing_path = tmp_path / "missing-file.txt"

    with pytest.raises(HyperbrowserError, match="Upload file not found"):
        manager.upload_file("session_123", missing_path)


def test_async_session_upload_file_raises_hyperbrowser_error_for_missing_path(tmp_path):
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))
    missing_path = tmp_path / "missing-file.txt"

    async def run():
        with pytest.raises(HyperbrowserError, match="Upload file not found"):
            await manager.upload_file("session_123", missing_path)

    asyncio.run(run())


def test_sync_session_upload_file_rejects_directory_path(tmp_path):
    manager = SyncSessionManager(_FakeClient(_SyncTransport()))

    with pytest.raises(HyperbrowserError, match="must point to a file"):
        manager.upload_file("session_123", tmp_path)


def test_async_session_upload_file_rejects_directory_path(tmp_path):
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport()))

    async def run():
        with pytest.raises(HyperbrowserError, match="must point to a file"):
            await manager.upload_file("session_123", tmp_path)

    asyncio.run(run())
