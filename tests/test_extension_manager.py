import asyncio
from contextlib import contextmanager
import io
from pathlib import Path
from types import SimpleNamespace
import pytest

import hyperbrowser.client.managers.async_manager.extension as async_extension_module
import hyperbrowser.client.managers.sync_manager.extension as sync_extension_module
from hyperbrowser.client.managers.async_manager.extension import (
    ExtensionManager as AsyncExtensionManager,
)
from hyperbrowser.client.managers.sync_manager.extension import (
    ExtensionManager as SyncExtensionManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _SyncTransport:
    def __init__(self):
        self.received_file = None
        self.received_data = None

    def post(self, url, data=None, files=None):
        assert url.endswith("/extensions/add")
        assert files is not None and "file" in files
        assert files["file"].closed is False
        self.received_file = files["file"]
        self.received_data = data
        return _FakeResponse(
            {
                "id": "ext_123",
                "name": "my-extension",
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
            }
        )

    def get(self, url, params=None, follow_redirects=False):
        assert url.endswith("/extensions/list")
        return _FakeResponse(
            {
                "extensions": [
                    {
                        "id": "ext_list_sync",
                        "name": "list-extension",
                        "createdAt": "2026-01-01T00:00:00Z",
                        "updatedAt": "2026-01-01T00:00:00Z",
                    }
                ]
            }
        )


class _AsyncTransport:
    def __init__(self):
        self.received_file = None
        self.received_data = None

    async def post(self, url, data=None, files=None):
        assert url.endswith("/extensions/add")
        assert files is not None and "file" in files
        assert files["file"].closed is False
        self.received_file = files["file"]
        self.received_data = data
        return _FakeResponse(
            {
                "id": "ext_456",
                "name": "my-extension",
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
            }
        )

    async def get(self, url, params=None, follow_redirects=False):
        assert url.endswith("/extensions/list")
        return _FakeResponse(
            {
                "extensions": [
                    {
                        "id": "ext_list_async",
                        "name": "list-extension",
                        "createdAt": "2026-01-01T00:00:00Z",
                        "updatedAt": "2026-01-01T00:00:00Z",
                    }
                ]
            }
        )


class _FakeClient:
    def __init__(self, transport):
        self.transport = transport

    def _build_url(self, path: str) -> str:
        return f"https://api.hyperbrowser.ai/api{path}"


def _create_test_extension_zip(tmp_path: Path) -> Path:
    file_path = tmp_path / "extension.zip"
    file_path.write_bytes(b"extension-bytes")
    return file_path


def test_sync_extension_create_does_not_mutate_params_and_closes_file(tmp_path):
    transport = _SyncTransport()
    manager = SyncExtensionManager(_FakeClient(transport))
    file_path = _create_test_extension_zip(tmp_path)
    params = CreateExtensionParams(name="my-extension", file_path=file_path)

    response = manager.create(params)

    assert response.id == "ext_123"
    assert params.file_path == file_path
    assert (
        transport.received_file is not None and transport.received_file.closed is True
    )
    assert transport.received_data == {"name": "my-extension"}


def test_sync_extension_create_uses_sanitized_open_error_message(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    params = CreateExtensionParams(name="my-extension", file_path="/tmp/ignored.zip")
    captured: dict[str, str] = {}

    @contextmanager
    def _open_binary_file_stub(file_path, *, open_error_message):  # type: ignore[no-untyped-def]
        captured["file_path"] = file_path
        captured["open_error_message"] = open_error_message
        yield io.BytesIO(b"content")

    monkeypatch.setattr(
        sync_extension_module,
        "normalize_extension_create_input",
        lambda _: ("bad\tpath.zip", {"name": "my-extension"}),
    )
    monkeypatch.setattr(
        sync_extension_module,
        "open_binary_file",
        _open_binary_file_stub,
    )
    monkeypatch.setattr(
        sync_extension_module,
        "create_extension_resource",
        lambda **kwargs: SimpleNamespace(id="ext_sync_mock"),
    )

    response = manager.create(params)

    assert response.id == "ext_sync_mock"
    assert captured["file_path"] == "bad\tpath.zip"
    assert (
        captured["open_error_message"]
        == "Failed to open extension file at path: bad?path.zip"
    )


def test_sync_extension_create_uses_metadata_open_file_prefix(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    manager._OPERATION_METADATA = type(
        "_Metadata",
        (),
        {
            "create_operation_name": "create extension",
            "open_file_error_prefix": "Custom extension open prefix",
        },
    )()
    params = CreateExtensionParams(name="my-extension", file_path="/tmp/ignored.zip")
    captured: dict[str, str] = {}

    @contextmanager
    def _open_binary_file_stub(file_path, *, open_error_message):  # type: ignore[no-untyped-def]
        captured["file_path"] = file_path
        captured["open_error_message"] = open_error_message
        yield io.BytesIO(b"content")

    monkeypatch.setattr(
        sync_extension_module,
        "normalize_extension_create_input",
        lambda _: ("bad\tpath.zip", {"name": "my-extension"}),
    )
    monkeypatch.setattr(
        sync_extension_module,
        "open_binary_file",
        _open_binary_file_stub,
    )
    monkeypatch.setattr(
        sync_extension_module,
        "create_extension_resource",
        lambda **kwargs: SimpleNamespace(id="ext_sync_mock"),
    )

    response = manager.create(params)

    assert response.id == "ext_sync_mock"
    assert captured["file_path"] == "bad\tpath.zip"
    assert captured["open_error_message"] == "Custom extension open prefix: bad?path.zip"


def test_sync_extension_create_uses_default_open_file_prefix_when_metadata_invalid(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    manager._OPERATION_METADATA = type(
        "_Metadata",
        (),
        {
            "create_operation_name": "create extension",
            "open_file_error_prefix": 123,
        },
    )()
    params = CreateExtensionParams(name="my-extension", file_path="/tmp/ignored.zip")
    captured: dict[str, str] = {}

    @contextmanager
    def _open_binary_file_stub(file_path, *, open_error_message):  # type: ignore[no-untyped-def]
        captured["file_path"] = file_path
        captured["open_error_message"] = open_error_message
        yield io.BytesIO(b"content")

    monkeypatch.setattr(
        sync_extension_module,
        "normalize_extension_create_input",
        lambda _: ("bad\tpath.zip", {"name": "my-extension"}),
    )
    monkeypatch.setattr(
        sync_extension_module,
        "open_binary_file",
        _open_binary_file_stub,
    )
    monkeypatch.setattr(
        sync_extension_module,
        "create_extension_resource",
        lambda **kwargs: SimpleNamespace(id="ext_sync_mock"),
    )

    response = manager.create(params)

    assert response.id == "ext_sync_mock"
    assert captured["file_path"] == "bad\tpath.zip"
    assert (
        captured["open_error_message"]
        == "Failed to open extension file at path: bad?path.zip"
    )


def test_async_extension_create_does_not_mutate_params_and_closes_file(tmp_path):
    transport = _AsyncTransport()
    manager = AsyncExtensionManager(_FakeClient(transport))
    file_path = _create_test_extension_zip(tmp_path)
    params = CreateExtensionParams(name="my-extension", file_path=file_path)

    async def run():
        return await manager.create(params)

    response = asyncio.run(run())

    assert response.id == "ext_456"
    assert params.file_path == file_path
    assert (
        transport.received_file is not None and transport.received_file.closed is True
    )
    assert transport.received_data == {"name": "my-extension"}


def test_async_extension_create_uses_sanitized_open_error_message(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    params = CreateExtensionParams(name="my-extension", file_path="/tmp/ignored.zip")
    captured: dict[str, str] = {}

    @contextmanager
    def _open_binary_file_stub(file_path, *, open_error_message):  # type: ignore[no-untyped-def]
        captured["file_path"] = file_path
        captured["open_error_message"] = open_error_message
        yield io.BytesIO(b"content")

    async def _create_extension_resource_async_stub(**kwargs):
        _ = kwargs
        return SimpleNamespace(id="ext_async_mock")

    monkeypatch.setattr(
        async_extension_module,
        "normalize_extension_create_input",
        lambda _: ("bad\tpath.zip", {"name": "my-extension"}),
    )
    monkeypatch.setattr(
        async_extension_module,
        "open_binary_file",
        _open_binary_file_stub,
    )
    monkeypatch.setattr(
        async_extension_module,
        "create_extension_resource_async",
        _create_extension_resource_async_stub,
    )

    async def run():
        return await manager.create(params)

    response = asyncio.run(run())

    assert response.id == "ext_async_mock"
    assert captured["file_path"] == "bad\tpath.zip"
    assert (
        captured["open_error_message"]
        == "Failed to open extension file at path: bad?path.zip"
    )


def test_async_extension_create_uses_metadata_open_file_prefix(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    manager._OPERATION_METADATA = type(
        "_Metadata",
        (),
        {
            "create_operation_name": "create extension",
            "open_file_error_prefix": "Custom extension open prefix",
        },
    )()
    params = CreateExtensionParams(name="my-extension", file_path="/tmp/ignored.zip")
    captured: dict[str, str] = {}

    @contextmanager
    def _open_binary_file_stub(file_path, *, open_error_message):  # type: ignore[no-untyped-def]
        captured["file_path"] = file_path
        captured["open_error_message"] = open_error_message
        yield io.BytesIO(b"content")

    async def _create_extension_resource_async_stub(**kwargs):
        _ = kwargs
        return SimpleNamespace(id="ext_async_mock")

    monkeypatch.setattr(
        async_extension_module,
        "normalize_extension_create_input",
        lambda _: ("bad\tpath.zip", {"name": "my-extension"}),
    )
    monkeypatch.setattr(
        async_extension_module,
        "open_binary_file",
        _open_binary_file_stub,
    )
    monkeypatch.setattr(
        async_extension_module,
        "create_extension_resource_async",
        _create_extension_resource_async_stub,
    )

    async def run():
        return await manager.create(params)

    response = asyncio.run(run())

    assert response.id == "ext_async_mock"
    assert captured["file_path"] == "bad\tpath.zip"
    assert captured["open_error_message"] == "Custom extension open prefix: bad?path.zip"


def test_async_extension_create_uses_default_open_file_prefix_when_metadata_invalid(
    monkeypatch: pytest.MonkeyPatch,
):
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    manager._OPERATION_METADATA = type(
        "_Metadata",
        (),
        {
            "create_operation_name": "create extension",
            "open_file_error_prefix": 123,
        },
    )()
    params = CreateExtensionParams(name="my-extension", file_path="/tmp/ignored.zip")
    captured: dict[str, str] = {}

    @contextmanager
    def _open_binary_file_stub(file_path, *, open_error_message):  # type: ignore[no-untyped-def]
        captured["file_path"] = file_path
        captured["open_error_message"] = open_error_message
        yield io.BytesIO(b"content")

    async def _create_extension_resource_async_stub(**kwargs):
        _ = kwargs
        return SimpleNamespace(id="ext_async_mock")

    monkeypatch.setattr(
        async_extension_module,
        "normalize_extension_create_input",
        lambda _: ("bad\tpath.zip", {"name": "my-extension"}),
    )
    monkeypatch.setattr(
        async_extension_module,
        "open_binary_file",
        _open_binary_file_stub,
    )
    monkeypatch.setattr(
        async_extension_module,
        "create_extension_resource_async",
        _create_extension_resource_async_stub,
    )

    async def run():
        return await manager.create(params)

    response = asyncio.run(run())

    assert response.id == "ext_async_mock"
    assert captured["file_path"] == "bad\tpath.zip"
    assert (
        captured["open_error_message"]
        == "Failed to open extension file at path: bad?path.zip"
    )


def test_sync_extension_create_raises_hyperbrowser_error_when_file_missing(tmp_path):
    transport = _SyncTransport()
    manager = SyncExtensionManager(_FakeClient(transport))
    missing_path = tmp_path / "missing-extension.zip"
    params = CreateExtensionParams(name="missing-extension", file_path=missing_path)

    with pytest.raises(HyperbrowserError, match="Extension file not found"):
        manager.create(params)


def test_async_extension_create_raises_hyperbrowser_error_when_file_missing(tmp_path):
    transport = _AsyncTransport()
    manager = AsyncExtensionManager(_FakeClient(transport))
    missing_path = tmp_path / "missing-extension.zip"
    params = CreateExtensionParams(name="missing-extension", file_path=missing_path)

    async def run():
        with pytest.raises(HyperbrowserError, match="Extension file not found"):
            await manager.create(params)

    asyncio.run(run())


def test_sync_extension_create_rejects_directory_path(tmp_path):
    transport = _SyncTransport()
    manager = SyncExtensionManager(_FakeClient(transport))
    params = CreateExtensionParams(name="dir-extension", file_path=tmp_path)

    with pytest.raises(HyperbrowserError, match="must point to a file"):
        manager.create(params)


def test_async_extension_create_rejects_directory_path(tmp_path):
    transport = _AsyncTransport()
    manager = AsyncExtensionManager(_FakeClient(transport))
    params = CreateExtensionParams(name="dir-extension", file_path=tmp_path)

    async def run():
        with pytest.raises(HyperbrowserError, match="must point to a file"):
            await manager.create(params)

    asyncio.run(run())


def test_sync_extension_list_returns_parsed_extensions():
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))

    extensions = manager.list()

    assert len(extensions) == 1
    assert extensions[0].id == "ext_list_sync"


def test_async_extension_list_returns_parsed_extensions():
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))

    async def run():
        return await manager.list()

    extensions = asyncio.run(run())

    assert len(extensions) == 1
    assert extensions[0].id == "ext_list_async"


def test_sync_extension_list_raises_for_invalid_payload_shape():
    class _InvalidSyncTransport:
        def get(self, url, params=None, follow_redirects=False):
            return _FakeResponse({"extensions": "not-a-list"})

    manager = SyncExtensionManager(_FakeClient(_InvalidSyncTransport()))

    with pytest.raises(HyperbrowserError, match="Expected list in 'extensions' key"):
        manager.list()


def test_sync_extension_create_rejects_invalid_params_type():
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))

    with pytest.raises(HyperbrowserError, match="params must be CreateExtensionParams"):
        manager.create({"name": "bad", "filePath": "/tmp/ext.zip"})  # type: ignore[arg-type]


def test_sync_extension_create_rejects_subclass_params(tmp_path):
    class _BrokenParams(CreateExtensionParams):
        pass

    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    params = _BrokenParams(
        name="bad-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    with pytest.raises(
        HyperbrowserError, match="params must be CreateExtensionParams"
    ) as exc_info:
        manager.create(params)

    assert exc_info.value.original_error is None


def test_sync_extension_create_wraps_param_serialization_errors(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(CreateExtensionParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extension create params"
    ) as exc_info:
        manager.create(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_sync_extension_create_preserves_hyperbrowser_param_serialization_errors(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(CreateExtensionParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        manager.create(params)

    assert exc_info.value.original_error is None


def test_async_extension_list_raises_for_invalid_payload_shape():
    class _InvalidAsyncTransport:
        async def get(self, url, params=None, follow_redirects=False):
            return _FakeResponse({"extensions": "not-a-list"})

    manager = AsyncExtensionManager(_FakeClient(_InvalidAsyncTransport()))

    async def run():
        with pytest.raises(
            HyperbrowserError, match="Expected list in 'extensions' key"
        ):
            await manager.list()

    asyncio.run(run())


def test_async_extension_create_rejects_invalid_params_type():
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))

    async def run():
        with pytest.raises(
            HyperbrowserError, match="params must be CreateExtensionParams"
        ):
            await manager.create(
                {"name": "bad", "filePath": "/tmp/ext.zip"}  # type: ignore[arg-type]
            )

    asyncio.run(run())


def test_async_extension_create_rejects_subclass_params(tmp_path):
    class _BrokenParams(CreateExtensionParams):
        pass

    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    params = _BrokenParams(
        name="bad-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    async def run():
        with pytest.raises(
            HyperbrowserError, match="params must be CreateExtensionParams"
        ) as exc_info:
            await manager.create(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


def test_async_extension_create_wraps_param_serialization_errors(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(CreateExtensionParams, "model_dump", _raise_model_dump_error)

    async def run():
        with pytest.raises(
            HyperbrowserError, match="Failed to serialize extension create params"
        ) as exc_info:
            await manager.create(params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


def test_async_extension_create_preserves_hyperbrowser_param_serialization_errors(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(CreateExtensionParams, "model_dump", _raise_model_dump_error)

    async def run():
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await manager.create(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())
