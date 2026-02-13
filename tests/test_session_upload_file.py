import asyncio
from pathlib import Path

from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)


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
    assert transport.received_file is not None and transport.received_file.closed is True


def test_async_session_upload_file_accepts_pathlike(tmp_path):
    file_path = _create_upload_file(tmp_path)
    transport = _AsyncTransport()
    manager = AsyncSessionManager(_FakeClient(transport))

    async def run():
        return await manager.upload_file("session_123", file_path)

    response = asyncio.run(run())

    assert response.file_name == "file.txt"
    assert transport.received_file is not None and transport.received_file.closed is True
