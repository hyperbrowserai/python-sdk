from copy import deepcopy
from types import SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.computer_action import (
    ComputerActionManager as AsyncComputerActionManager,
)
from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxManager as AsyncSandboxManager,
)
from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_files import (
    SandboxFilesApi as AsyncSandboxFilesApi,
)
from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as AsyncSandboxProcessesApi,
)
from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_terminal import (
    SandboxTerminalApi as AsyncSandboxTerminalApi,
)
from hyperbrowser.client.managers.sync_manager.computer_action import (
    ComputerActionManager,
)
from hyperbrowser.client.managers.sync_manager.sandbox import SandboxManager
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_files import (
    SandboxFilesApi,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_terminal import (
    SandboxTerminalApi,
)
from hyperbrowser.models import (
    Coordinate,
    CreateSandboxParams,
    DragActionParams,
    SandboxExecParams,
    SandboxExposeParams,
    SandboxFileChmodParams,
    SandboxFileChownParams,
    SandboxFileCopyParams,
    SandboxFileWriteEntry,
    SandboxImageListParams,
    SandboxListParams,
    SandboxMemorySnapshotParams,
    SandboxNetworkPolicy,
    SandboxProcessStdinParams,
    SandboxSnapshotListParams,
    SandboxTerminalCreateParams,
)
from tests.test_sandbox_wire_contract import (
    MOVE_FILE_PAYLOAD,
    PROCESS_RESULT_PAYLOAD,
    PROCESS_SUMMARY_PAYLOAD,
    PTY_PAYLOAD,
    WRITE_FILE_PAYLOAD,
    FakeAsyncClient as SandboxFakeAsyncClient,
    FakeSyncClient as SandboxFakeSyncClient,
)


LIST_PARAMS = {
    "status": "active",
    "page": 2,
    "limit": 5,
    "start": 100,
    "end": 200,
    "search": "sandbox",
}
IMAGE_LIST_PARAMS = {
    "page": 2,
    "limit": 5,
    "search": "node",
    "sources": ["registry", "uploaded"],
}
SNAPSHOT_LIST_PARAMS = {
    "status": ["created", "failed"],
    "limit": 10,
    "image_name": "node",
    "search": "snap",
    "page": 2,
}
CREATE_PARAMS = {
    "image_name": "node",
    "image_id": "img-id",
    "cpu": 4,
    "memory_mib": 4096,
    "disk_mib": 8192,
    "enable_recording": True,
    "exposed_ports": [{"port": 3000, "auth": True}],
    "mounts": {
        "/workspace/cache": {
            "id": "2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
            "type": "rw",
            "shared": True,
        }
    },
    "timeout_minutes": 15,
    "allow_internet_access": False,
    "allow_out": ["1.1.1.1", "example.com"],
    "deny_out": ["0.0.0.0/0"],
}
SNAPSHOT_PARAMS = {"snapshot_name": "snap"}
NETWORK_POLICY = {"allow_internet_access": False}
EXPOSE_PARAMS = {"port": 3000, "auth": True}


def _control_inputs(use_models):
    if not use_models:
        return (
            deepcopy(LIST_PARAMS),
            deepcopy(IMAGE_LIST_PARAMS),
            deepcopy(SNAPSHOT_LIST_PARAMS),
            deepcopy(CREATE_PARAMS),
            deepcopy(SNAPSHOT_PARAMS),
            deepcopy(NETWORK_POLICY),
            deepcopy(EXPOSE_PARAMS),
        )
    return (
        SandboxListParams(**LIST_PARAMS),
        SandboxImageListParams(**IMAGE_LIST_PARAMS),
        SandboxSnapshotListParams(**SNAPSHOT_LIST_PARAMS),
        CreateSandboxParams(**CREATE_PARAMS),
        SandboxMemorySnapshotParams(**SNAPSHOT_PARAMS),
        SandboxNetworkPolicy(**NETWORK_POLICY),
        SandboxExposeParams(**EXPOSE_PARAMS),
    )


def _exercise_sync_control_surface(use_models):
    client = SandboxFakeSyncClient()
    manager = SandboxManager(client)
    (
        list_params,
        image_list_params,
        snapshot_list_params,
        create_params,
        snapshot_params,
        network_policy,
        expose_params,
    ) = _control_inputs(use_models)

    manager.list(list_params)
    manager.list_images(image_list_params)
    manager.list_snapshots(snapshot_list_params)
    manager.create(create_params)
    manager.create_memory_snapshot("sbx_123", snapshot_params)
    manager.update_network("sbx_123", network_policy)
    manager.expose(
        "sbx_123",
        expose_params,
        runtime=SimpleNamespace(base_url="https://runtime.example.com"),
    )
    return client.transport.client.calls


async def _exercise_async_control_surface(use_models):
    client = SandboxFakeAsyncClient()
    manager = AsyncSandboxManager(client)
    (
        list_params,
        image_list_params,
        snapshot_list_params,
        create_params,
        snapshot_params,
        network_policy,
        expose_params,
    ) = _control_inputs(use_models)

    await manager.list(list_params)
    await manager.list_images(image_list_params)
    await manager.list_snapshots(snapshot_list_params)
    await manager.create(create_params)
    await manager.create_memory_snapshot("sbx_123", snapshot_params)
    await manager.update_network("sbx_123", network_policy)
    await manager.expose(
        "sbx_123",
        expose_params,
        runtime=SimpleNamespace(base_url="https://runtime.example.com"),
    )
    return client.transport.client.calls


def test_sync_sandbox_lifecycle_dicts_match_legacy_models_on_the_wire():
    assert _exercise_sync_control_surface(False) == _exercise_sync_control_surface(True)


@pytest.mark.anyio
async def test_async_sandbox_lifecycle_dicts_match_legacy_models_on_the_wire():
    assert await _exercise_async_control_surface(
        False
    ) == await _exercise_async_control_surface(True)


class RecordingRuntimeTransport:
    def __init__(self):
        self.calls = []

    def request_json(
        self,
        path,
        *,
        method="GET",
        params=None,
        json_body=None,
        content=None,
        headers=None,
    ):
        self.calls.append(
            {
                "path": path,
                "method": method,
                "params": params,
                "json_body": json_body,
                "content": content,
                "headers": headers,
            }
        )
        return _runtime_response(path, method)


class AsyncRecordingRuntimeTransport(RecordingRuntimeTransport):
    async def request_json(
        self,
        path,
        *,
        method="GET",
        params=None,
        json_body=None,
        content=None,
        headers=None,
    ):
        return super().request_json(
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )


def _runtime_response(path, method):
    if path == "/sandbox/exec":
        return PROCESS_RESULT_PAYLOAD
    if path == "/sandbox/processes" and method == "POST":
        return PROCESS_SUMMARY_PAYLOAD
    if path.endswith("/stdin"):
        return {}
    if path == "/sandbox/pty":
        return PTY_PAYLOAD
    if path == "/sandbox/files/write":
        return WRITE_FILE_PAYLOAD
    if path == "/sandbox/files/copy":
        return MOVE_FILE_PAYLOAD
    if path in {"/sandbox/files/chmod", "/sandbox/files/chown"}:
        return {}
    raise AssertionError(f"Unexpected request: {method} {path}")


EXEC_PARAMS = {
    "command": "echo",
    "args": ["hi world"],
    "timeout_ms": 500,
    "timeout_sec": 7,
    "run_as": "root",
}
STDIN_PARAMS = {"data": b"hello", "eof": True}
TERMINAL_PARAMS = {
    "command": "bash",
    "use_shell": False,
    "rows": 24,
    "cols": 80,
    "timeout_ms": 1500,
}
WRITE_ENTRY = {
    "path": "/tmp/a.txt",
    "data": b"hello",
    "append": True,
    "mode": "600",
}
COPY_PARAMS = {
    "source": "/tmp/a.txt",
    "destination": "/tmp/b.txt",
    "recursive": False,
    "overwrite": True,
}
CHMOD_PARAMS = {"path": "/tmp/b.txt", "mode": "640", "recursive": False}
CHOWN_PARAMS = {"path": "/tmp/b.txt", "uid": 1000, "gid": 1000, "recursive": True}


def _runtime_inputs(use_models):
    if not use_models:
        return (
            deepcopy(EXEC_PARAMS),
            deepcopy(STDIN_PARAMS),
            deepcopy(TERMINAL_PARAMS),
            deepcopy(WRITE_ENTRY),
            deepcopy(COPY_PARAMS),
            deepcopy(CHMOD_PARAMS),
            deepcopy(CHOWN_PARAMS),
        )
    return (
        SandboxExecParams(**EXEC_PARAMS),
        SandboxProcessStdinParams(**STDIN_PARAMS),
        SandboxTerminalCreateParams(**TERMINAL_PARAMS),
        SandboxFileWriteEntry(**WRITE_ENTRY),
        SandboxFileCopyParams(**COPY_PARAMS),
        SandboxFileChmodParams(**CHMOD_PARAMS),
        SandboxFileChownParams(**CHOWN_PARAMS),
    )


def _exercise_sync_runtime_surface(use_models):
    transport = RecordingRuntimeTransport()
    (
        exec_params,
        stdin_params,
        terminal_params,
        write_entry,
        copy_params,
        chmod_params,
        chown_params,
    ) = _runtime_inputs(use_models)

    processes = SandboxProcessesApi(transport)
    processes.exec(exec_params)
    process = processes.start(exec_params)
    process.write_stdin(stdin_params)

    SandboxTerminalApi(transport, lambda: None).create(terminal_params)

    files = SandboxFilesApi(transport, lambda: None)
    files.write([write_entry])
    files.copy(copy_params)
    files.chmod(chmod_params)
    files.chown(chown_params)
    return transport.calls


async def _exercise_async_runtime_surface(use_models):
    transport = AsyncRecordingRuntimeTransport()
    (
        exec_params,
        stdin_params,
        terminal_params,
        write_entry,
        copy_params,
        chmod_params,
        chown_params,
    ) = _runtime_inputs(use_models)

    processes = AsyncSandboxProcessesApi(transport)
    await processes.exec(exec_params)
    process = await processes.start(exec_params)
    await process.write_stdin(stdin_params)

    await AsyncSandboxTerminalApi(transport, lambda: None).create(terminal_params)

    files = AsyncSandboxFilesApi(transport, lambda: None)
    await files.write([write_entry])
    await files.copy(copy_params)
    await files.chmod(chmod_params)
    await files.chown(chown_params)
    return transport.calls


def test_sync_sandbox_runtime_dicts_match_legacy_models_on_the_wire():
    assert _exercise_sync_runtime_surface(False) == _exercise_sync_runtime_surface(True)


@pytest.mark.anyio
async def test_async_sandbox_runtime_dicts_match_legacy_models_on_the_wire():
    assert await _exercise_async_runtime_surface(
        False
    ) == await _exercise_async_runtime_surface(True)


class RecordingComputerActionTransport:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None):
        self.calls.append({"url": url, "data": data})
        return SimpleNamespace(data={"success": True})


class AsyncRecordingComputerActionTransport:
    def __init__(self):
        self.calls = []

    async def post(self, url, data=None):
        self.calls.append({"url": url, "data": data})
        return SimpleNamespace(data={"success": True})


def _computer_action_session():
    return SimpleNamespace(
        computer_action_endpoint="https://computer-action.example.com",
    )


def test_sync_computer_action_dicts_match_legacy_models_on_the_wire():
    legacy_client = SimpleNamespace(transport=RecordingComputerActionTransport())
    dict_client = SimpleNamespace(transport=RecordingComputerActionTransport())
    legacy_manager = ComputerActionManager(legacy_client)
    dict_manager = ComputerActionManager(dict_client)
    legacy = DragActionParams(
        path=[Coordinate(x=10, y=20), Coordinate(x=30, y=40)],
        return_screenshot=True,
    )
    mapping = {
        "action": "drag",
        "path": [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
        "return_screenshot": True,
    }

    legacy_manager._execute_request(_computer_action_session(), legacy)
    dict_manager._execute_request(_computer_action_session(), mapping)

    assert dict_client.transport.calls == legacy_client.transport.calls

    legacy_client.transport.calls.clear()
    dict_client.transport.calls.clear()
    legacy_manager.drag(
        _computer_action_session(),
        [Coordinate(x=10, y=20), Coordinate(x=30, y=40)],
        return_screenshot=True,
    )
    dict_manager.drag(
        _computer_action_session(),
        [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
        return_screenshot=True,
    )

    assert dict_client.transport.calls == legacy_client.transport.calls


@pytest.mark.anyio
async def test_async_computer_action_dicts_match_legacy_models_on_the_wire():
    legacy_client = SimpleNamespace(transport=AsyncRecordingComputerActionTransport())
    dict_client = SimpleNamespace(transport=AsyncRecordingComputerActionTransport())
    legacy_manager = AsyncComputerActionManager(legacy_client)
    dict_manager = AsyncComputerActionManager(dict_client)
    legacy = DragActionParams(
        path=[Coordinate(x=10, y=20), Coordinate(x=30, y=40)],
        return_screenshot=True,
    )
    mapping = {
        "action": "drag",
        "path": [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
        "return_screenshot": True,
    }

    await legacy_manager._execute_request(_computer_action_session(), legacy)
    await dict_manager._execute_request(_computer_action_session(), mapping)

    assert dict_client.transport.calls == legacy_client.transport.calls

    legacy_client.transport.calls.clear()
    dict_client.transport.calls.clear()
    await legacy_manager.drag(
        _computer_action_session(),
        [Coordinate(x=10, y=20), Coordinate(x=30, y=40)],
        return_screenshot=True,
    )
    await dict_manager.drag(
        _computer_action_session(),
        [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
        return_screenshot=True,
    )

    assert dict_client.transport.calls == legacy_client.transport.calls
