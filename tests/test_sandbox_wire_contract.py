import httpx
import pytest

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
    CreateSandboxParams,
    SandboxExecParams,
    SandboxListParams,
    SandboxMemorySnapshotParams,
    SandboxPresignFileParams,
    SandboxProcessListParams,
    SandboxProcessWaitParams,
    SandboxTerminalCreateParams,
    SandboxTerminalKillParams,
    SandboxTerminalWaitParams,
)


SANDBOX_DETAIL_PAYLOAD = {
    "id": "sbx_123",
    "teamId": "team_1",
    "status": "active",
    "endTime": None,
    "startTime": 123,
    "createdAt": "2026-03-12T00:00:00Z",
    "updatedAt": "2026-03-12T00:00:01Z",
    "closeReason": None,
    "dataConsumed": 1,
    "proxyDataConsumed": 2,
    "usageType": "sandbox",
    "jobId": None,
    "launchState": None,
    "creditsUsed": 0.1,
    "region": "us",
    "sessionUrl": "https://example.com/session",
    "duration": 10,
    "proxyBytesUsed": 3,
    "runtime": {
        "transport": "regional_proxy",
        "host": "runtime.example.com",
        "baseUrl": "https://runtime.example.com",
    },
    "token": "tok",
    "tokenExpiresAt": "2026-03-12T01:00:00Z",
}

SNAPSHOT_RESULT_PAYLOAD = {
    "snapshotName": "snap",
    "snapshotId": "sid",
    "namespace": "ns",
    "status": "ready",
    "imageName": "img",
    "imageId": "iid",
    "imageNamespace": "ins",
}

SANDBOX_LIST_PAYLOAD = {
    "sandboxes": [
        {
            "id": "sbx_123",
            "teamId": "team_1",
            "status": "active",
            "endTime": None,
            "startTime": 123,
            "createdAt": "2026-03-12T00:00:00Z",
            "updatedAt": "2026-03-12T00:00:01Z",
            "closeReason": None,
            "dataConsumed": 1,
            "proxyDataConsumed": 2,
            "usageType": "sandbox",
            "jobId": None,
            "launchState": None,
            "creditsUsed": 0.1,
            "region": "us",
            "sessionUrl": "https://example.com/session",
            "duration": 10,
            "proxyBytesUsed": 3,
            "runtime": {
                "transport": "regional_proxy",
                "host": "runtime.example.com",
                "baseUrl": "https://runtime.example.com",
            },
        }
    ],
    "totalCount": 1,
    "page": 2,
    "perPage": 5,
}

IMAGE_LIST_PAYLOAD = {
    "images": [
        {
            "id": "img_123",
            "imageName": "node",
            "namespace": "team_1",
            "uploaded": True,
            "createdAt": "2026-03-12T00:00:00Z",
            "updatedAt": "2026-03-12T00:00:01Z",
        }
    ]
}

SNAPSHOT_LIST_PAYLOAD = {
    "snapshots": [
        {
            "id": "snap_123",
            "snapshotName": "snapshot-1",
            "namespace": "team_1",
            "imageNamespace": "team_1",
            "imageName": "node",
            "imageId": "img_123",
            "status": "created",
            "compatibilityTag": None,
            "metadata": {},
            "uploaded": True,
            "createdAt": "2026-03-12T00:00:00Z",
            "updatedAt": "2026-03-12T00:00:01Z",
        }
    ]
}

PROCESS_RESULT_PAYLOAD = {
    "result": {
        "id": "proc_1",
        "status": "exited",
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "started_at": 1,
        "completed_at": 2,
        "error": None,
    }
}

PROCESS_SUMMARY_PAYLOAD = {
    "process": {
        "id": "proc_1",
        "status": "running",
        "command": "bash",
        "args": ["-lc", "echo hi"],
        "cwd": "/tmp",
        "pid": 123,
        "exit_code": None,
        "started_at": 1,
        "completed_at": None,
    }
}

PROCESS_LIST_PAYLOAD = {
    "data": [],
    "next_cursor": None,
}

PTY_PAYLOAD = {
    "pty": {
        "id": "pty_1",
        "command": "bash",
        "args": ["-lc"],
        "cwd": "/tmp",
        "pid": 321,
        "running": True,
        "exitCode": None,
        "error": None,
        "timedOut": False,
        "rows": 24,
        "cols": 80,
        "startedAt": 1,
        "finishedAt": None,
        "output": [],
    }
}

WATCH_PAYLOAD = {
    "watch": {
        "id": "watch_1",
        "path": "/tmp",
        "recursive": False,
        "active": True,
        "error": None,
        "createdAt": 1,
        "stoppedAt": None,
        "oldestSeq": 0,
        "lastSeq": 0,
        "eventCount": 0,
    }
}

UPLOAD_PRESIGN_PAYLOAD = {
    "token": "upload-token",
    "path": "/tmp/file.txt",
    "method": "PUT",
    "expiresAt": 123,
    "url": "https://example.com/upload",
}

DOWNLOAD_PRESIGN_PAYLOAD = {
    "token": "download-token",
    "path": "/tmp/file.txt",
    "method": "GET",
    "expiresAt": 123,
    "url": "https://example.com/download",
}

MOVE_FILE_PAYLOAD = {
    "entry": {
        "path": "/tmp/destination.txt",
        "name": "destination.txt",
        "type": "file",
        "size": 14,
        "mode": 420,
        "permissions": "-rw-r--r--",
        "owner": "root",
        "group": "root",
        "modifiedTime": 123,
        "symlinkTarget": None,
    }
}


class RecordingHTTPClient:
    def __init__(self):
        self.calls = []

    def request(self, method, url, params=None, json=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
            }
        )

        if url.endswith("/sandboxes"):
            payload = SANDBOX_LIST_PAYLOAD
        elif url.endswith("/images"):
            payload = IMAGE_LIST_PAYLOAD
        elif url.endswith("/snapshots"):
            payload = SNAPSHOT_LIST_PAYLOAD
        elif url.endswith("/sandbox"):
            payload = SANDBOX_DETAIL_PAYLOAD
        elif url.endswith("/snapshot"):
            payload = SNAPSHOT_RESULT_PAYLOAD
        else:
            payload = {}

        return httpx.Response(
            200,
            json=payload,
            request=httpx.Request(method, url),
        )


class RecordingTransport:
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

        if path == "/sandbox/exec":
            return PROCESS_RESULT_PAYLOAD
        if path == "/sandbox/processes" and method == "POST":
            return PROCESS_SUMMARY_PAYLOAD
        if path == "/sandbox/processes":
            return PROCESS_LIST_PAYLOAD
        if path.endswith("/wait") and "/sandbox/processes/" in path:
            return PROCESS_RESULT_PAYLOAD
        if path == "/sandbox/pty" or path.startswith("/sandbox/pty/"):
            return PTY_PAYLOAD
        if path.startswith("/sandbox/files/watch/"):
            return WATCH_PAYLOAD
        if path == "/sandbox/files/presign-upload":
            return UPLOAD_PRESIGN_PAYLOAD
        if path == "/sandbox/files/presign-download":
            return DOWNLOAD_PRESIGN_PAYLOAD
        if path == "/sandbox/files/move":
            return MOVE_FILE_PAYLOAD
        raise AssertionError(f"Unexpected request path: {path}")


class AsyncRecordingTransport(RecordingTransport):
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


class FakeSyncClient:
    def __init__(self):
        http_client = RecordingHTTPClient()
        self.transport = type("Transport", (), {"client": http_client})()
        self.config = type("Config", (), {"runtime_proxy_override": None})()
        self.timeout = 30

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


class RecordingAsyncHTTPClient:
    def __init__(self):
        self.calls = []

    async def request(self, method, url, params=None, json=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
            }
        )

        if url.endswith("/sandboxes"):
            payload = SANDBOX_LIST_PAYLOAD
        elif url.endswith("/images"):
            payload = IMAGE_LIST_PAYLOAD
        elif url.endswith("/snapshots"):
            payload = SNAPSHOT_LIST_PAYLOAD
        elif url.endswith("/sandbox"):
            payload = SANDBOX_DETAIL_PAYLOAD
        elif url.endswith("/snapshot"):
            payload = SNAPSHOT_RESULT_PAYLOAD
        else:
            payload = {}

        return httpx.Response(
            200,
            json=payload,
            request=httpx.Request(method, url),
        )


class FakeAsyncClient:
    def __init__(self):
        http_client = RecordingAsyncHTTPClient()
        self.transport = type("Transport", (), {"client": http_client})()
        self.config = type("Config", (), {"runtime_proxy_override": None})()
        self.timeout = 30

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


def test_sandbox_request_models_serialize_expected_wire_keys():
    assert SandboxListParams(
        status="active",
        page=2,
        limit=5,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "status": "active",
        "page": 2,
        "limit": 5,
    }

    assert CreateSandboxParams(
        image_name="node",
        image_id="img-id",
        enable_recording=True,
        timeout_minutes=15,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "imageName": "node",
        "imageId": "img-id",
        "enableRecording": True,
        "timeoutMinutes": 15,
    }

    assert SandboxMemorySnapshotParams(snapshot_name="snap").model_dump(
        by_alias=True, exclude_none=True
    ) == {
        "snapshotName": "snap",
    }

    assert SandboxExecParams(
        command="echo hi",
        timeout_ms=500,
        timeout_sec=7,
        use_shell=True,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "useShell": True,
    }

    assert SandboxProcessWaitParams(
        timeout_ms=250,
        timeout_sec=3,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "timeoutMs": 250,
        "timeout_sec": 3,
    }

    assert SandboxProcessListParams(
        status=["running", "exited"],
        limit=10,
        cursor="cursor-1",
        created_after=100,
        created_before=200,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "status": ["running", "exited"],
        "limit": 10,
        "cursor": "cursor-1",
        "created_after": 100,
        "created_before": 200,
    }

    assert SandboxPresignFileParams(
        path="/tmp/file.txt",
        expires_in_seconds=60,
        one_time=True,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 60,
        "oneTime": True,
    }

    assert SandboxTerminalCreateParams(
        command="bash",
        use_shell=False,
        rows=24,
        cols=80,
        timeout_ms=1500,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "command": "bash",
        "useShell": False,
        "rows": 24,
        "cols": 80,
        "timeoutMs": 1500,
    }

    assert SandboxTerminalWaitParams(
        timeout_ms=800,
        include_output=True,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "timeoutMs": 800,
        "includeOutput": True,
    }

    assert SandboxTerminalKillParams(
        signal="TERM",
        timeout_ms=900,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "signal": "TERM",
        "timeoutMs": 900,
    }


def test_sync_sandbox_control_manager_uses_expected_wire_keys():
    client = FakeSyncClient()
    manager = SandboxManager(client)

    listed = manager.list(
        SandboxListParams(
            status="active",
            page=2,
            limit=5,
        )
    )
    images = manager.list_images()
    snapshots = manager.list_snapshots()
    manager.create(
        CreateSandboxParams(
            image_name="node",
            image_id="img-id",
            enable_recording=True,
            timeout_minutes=15,
        )
    )
    manager.create_memory_snapshot(
        "sbx_123",
        SandboxMemorySnapshotParams(snapshot_name="snap"),
    )

    list_call = client.transport.client.calls[0]
    images_call = client.transport.client.calls[1]
    snapshots_call = client.transport.client.calls[2]
    create_call = client.transport.client.calls[3]
    snapshot_call = client.transport.client.calls[4]

    assert list_call["params"] == {
        "status": "active",
        "page": 2,
        "limit": 5,
    }
    assert listed.total_count == 1
    assert listed.page == 2
    assert listed.per_page == 5
    assert images_call["url"].endswith("/images")
    assert images[0].image_name == "node"
    assert snapshots_call["url"].endswith("/snapshots")
    assert snapshots[0].compatibility_tag is None
    assert create_call["json"] == {
        "imageName": "node",
        "imageId": "img-id",
        "enableRecording": True,
        "timeoutMinutes": 15,
    }
    assert snapshot_call["json"] == {
        "snapshotName": "snap",
    }


def test_sync_sandbox_runtime_apis_use_expected_wire_keys():
    transport = RecordingTransport()

    processes = SandboxProcessesApi(transport)
    process_input = SandboxExecParams(
        command="echo hi",
        timeout_ms=500,
        timeout_sec=7,
        use_shell=True,
    )

    processes.exec(process_input)
    handle = processes.start(process_input)
    handle.wait(timeout_ms=250, timeout_sec=3)
    processes.list(
        status=["running", "exited"],
        limit=10,
        cursor="cursor-1",
        created_after=100,
        created_before=200,
    )

    terminal = SandboxTerminalApi(transport, lambda: None)
    terminal_handle = terminal.create(
        SandboxTerminalCreateParams(
            command="bash",
            use_shell=False,
            rows=24,
            cols=80,
            timeout_ms=1500,
        )
    )
    terminal.get("pty_1", include_output=True)
    terminal_handle.wait(timeout_ms=800, include_output=True)

    files = SandboxFilesApi(transport, lambda: None)
    files.get_watch("watch_1", include_events=True)
    files.upload_url("/tmp/file.txt", expires_in_seconds=60, one_time=True)
    files.download_url("/tmp/file.txt", expires_in_seconds=30, one_time=False)
    files.move(
        source="/tmp/source.txt",
        destination="/tmp/destination.txt",
        overwrite=True,
    )

    assert transport.calls[0]["json_body"] == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "useShell": True,
    }
    assert transport.calls[1]["json_body"] == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "useShell": True,
    }
    assert transport.calls[2]["json_body"] == {
        "timeoutMs": 250,
        "timeout_sec": 3,
    }
    assert transport.calls[3]["params"] == {
        "status": "running,exited",
        "limit": 10,
        "cursor": "cursor-1",
        "created_after": 100,
        "created_before": 200,
    }
    assert transport.calls[4]["json_body"] == {
        "command": "bash",
        "useShell": False,
        "rows": 24,
        "cols": 80,
        "timeoutMs": 1500,
    }
    assert transport.calls[5]["params"] == {"includeOutput": True}
    assert transport.calls[6]["json_body"] == {
        "timeoutMs": 800,
        "includeOutput": True,
    }
    assert transport.calls[7]["params"] == {"includeEvents": True}
    assert transport.calls[8]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 60,
        "oneTime": True,
    }
    assert transport.calls[9]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 30,
        "oneTime": False,
    }
    assert transport.calls[10]["json_body"] == {
        "from": "/tmp/source.txt",
        "to": "/tmp/destination.txt",
        "overwrite": True,
    }


@pytest.mark.anyio
async def test_async_sandbox_control_manager_uses_expected_wire_keys():
    client = FakeAsyncClient()
    manager = AsyncSandboxManager(client)

    listed = await manager.list(
        SandboxListParams(
            status="active",
            page=2,
            limit=5,
        )
    )
    images = await manager.list_images()
    snapshots = await manager.list_snapshots()
    await manager.create(
        CreateSandboxParams(
            image_name="node",
            image_id="img-id",
            enable_recording=True,
            timeout_minutes=15,
        )
    )
    await manager.create_memory_snapshot(
        "sbx_123",
        SandboxMemorySnapshotParams(snapshot_name="snap"),
    )

    list_call = client.transport.client.calls[0]
    images_call = client.transport.client.calls[1]
    snapshots_call = client.transport.client.calls[2]
    create_call = client.transport.client.calls[3]
    snapshot_call = client.transport.client.calls[4]

    assert list_call["params"] == {
        "status": "active",
        "page": 2,
        "limit": 5,
    }
    assert listed.total_count == 1
    assert listed.page == 2
    assert listed.per_page == 5
    assert images_call["url"].endswith("/images")
    assert images[0].image_name == "node"
    assert snapshots_call["url"].endswith("/snapshots")
    assert snapshots[0].compatibility_tag is None
    assert create_call["json"] == {
        "imageName": "node",
        "imageId": "img-id",
        "enableRecording": True,
        "timeoutMinutes": 15,
    }
    assert snapshot_call["json"] == {
        "snapshotName": "snap",
    }


@pytest.mark.anyio
async def test_async_sandbox_runtime_apis_use_expected_wire_keys():
    transport = AsyncRecordingTransport()

    processes = AsyncSandboxProcessesApi(transport)
    process_input = SandboxExecParams(
        command="echo hi",
        timeout_ms=500,
        timeout_sec=7,
        use_shell=True,
    )

    await processes.exec(process_input)
    handle = await processes.start(process_input)
    await handle.wait(timeout_ms=250, timeout_sec=3)
    await processes.list(
        status=["running", "exited"],
        limit=10,
        cursor="cursor-1",
        created_after=100,
        created_before=200,
    )

    terminal = AsyncSandboxTerminalApi(transport, lambda: None)
    terminal_handle = await terminal.create(
        SandboxTerminalCreateParams(
            command="bash",
            use_shell=False,
            rows=24,
            cols=80,
            timeout_ms=1500,
        )
    )
    await terminal.get("pty_1", include_output=True)
    await terminal_handle.wait(timeout_ms=800, include_output=True)

    files = AsyncSandboxFilesApi(transport, lambda: None)
    await files.get_watch("watch_1", include_events=True)
    await files.upload_url("/tmp/file.txt", expires_in_seconds=60, one_time=True)
    await files.download_url("/tmp/file.txt", expires_in_seconds=30, one_time=False)
    await files.move(
        source="/tmp/source.txt",
        destination="/tmp/destination.txt",
        overwrite=True,
    )

    assert transport.calls[0]["json_body"] == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "useShell": True,
    }
    assert transport.calls[1]["json_body"] == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "useShell": True,
    }
    assert transport.calls[2]["json_body"] == {
        "timeoutMs": 250,
        "timeout_sec": 3,
    }
    assert transport.calls[3]["params"] == {
        "status": "running,exited",
        "limit": 10,
        "cursor": "cursor-1",
        "created_after": 100,
        "created_before": 200,
    }
    assert transport.calls[4]["json_body"] == {
        "command": "bash",
        "useShell": False,
        "rows": 24,
        "cols": 80,
        "timeoutMs": 1500,
    }
    assert transport.calls[5]["params"] == {"includeOutput": True}
    assert transport.calls[6]["json_body"] == {
        "timeoutMs": 800,
        "includeOutput": True,
    }
    assert transport.calls[7]["params"] == {"includeEvents": True}
    assert transport.calls[8]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 60,
        "oneTime": True,
    }
    assert transport.calls[9]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 30,
        "oneTime": False,
    }
    assert transport.calls[10]["json_body"] == {
        "from": "/tmp/source.txt",
        "to": "/tmp/destination.txt",
        "overwrite": True,
    }
