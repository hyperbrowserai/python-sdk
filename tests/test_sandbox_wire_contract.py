import io
import httpx
import pytest
from types import SimpleNamespace
import hyperbrowser.client.managers.async_manager.sandboxes.sandbox_terminal as async_terminal_module
import hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_terminal as sync_terminal_module

from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxHandle as AsyncSandboxHandle,
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
from hyperbrowser.client.managers.sync_manager.sandbox import (
    SandboxHandle,
    SandboxManager,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_files import (
    SandboxFilesApi,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_terminal import (
    SandboxTerminalApi,
)
from hyperbrowser.client.managers.sandboxes.shared import _build_sandbox_exposed_url
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CompleteSandboxImageBuildParams,
    CreateSandboxParams,
    CreateSandboxImageBuildParams,
    ReuseSandboxDockerImageParams,
    SandboxDetail,
    SandboxExposeParams,
    SandboxExecParams,
    SandboxFileWriteEntry,
    SandboxImageInit,
    SandboxImageBuildListParams,
    SandboxImageListParams,
    SandboxListParams,
    SandboxMemorySnapshotParams,
    SandboxNetworkPolicy,
    SandboxPresignFileParams,
    SandboxProcessListParams,
    SandboxProcessResult,
    SandboxProcessSummary,
    SandboxProcessWaitParams,
    SandboxSnapshotListParams,
    SandboxSnapshotSummary,
    SandboxTerminalCreateParams,
    SandboxTerminalKillParams,
    SandboxTerminalWaitParams,
    SandboxUnexposeResult,
    SandboxVolumeMount,
    StartSandboxFromSnapshotParams,
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
    "vcpus": 2,
    "memMiB": 2048,
    "diskSizeMiB": 8192,
    "timeoutMinutes": 30,
    "runtime": {
        "transport": "regional_proxy",
        "host": "https://runtime.example.com",
        "baseUrl": "https://runtime.example.com/sandbox/sbx_123",
    },
    "exposedPorts": [
        {
            "port": 3000,
            "auth": True,
            "url": "https://3000-sbx_123.runtime.example.com/",
            "browserUrl": "https://3000-sbx_123.runtime.example.com/_hb/auth?grant=test&next=%2F",
            "browserUrlExpiresAt": "2026-03-12T02:00:00Z",
        }
    ],
    "network": {
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1"],
        "denyOut": ["0.0.0.0/0"],
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
            "vcpus": 2,
            "memMiB": 2048,
            "diskSizeMiB": 8192,
            "runtime": {
                "transport": "regional_proxy",
                "host": "https://runtime.example.com",
                "baseUrl": "https://runtime.example.com/sandbox/sbx_123",
            },
            "exposedPorts": [
                {
                    "port": 3000,
                    "auth": False,
                    "url": "https://3000-sbx_123.runtime.example.com/",
                    "browserUrl": "https://3000-sbx_123.runtime.example.com/",
                }
            ],
            "network": {
                "allowInternetAccess": True,
                "allowOut": [],
                "denyOut": [],
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
            "source": "registry",
            "imageInit": {"args": ["node", "server.js"]},
            "uploaded": True,
            "createdAt": "2026-03-12T00:00:00Z",
            "updatedAt": "2026-03-12T00:00:01Z",
        }
    ],
    "totalCount": 1,
    "page": 2,
    "perPage": 5,
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
            "vcpus": 2,
            "memMiB": 2048,
            "diskSizeMiB": 8192,
            "compatibilityTag": None,
            "metadata": {},
            "uploaded": True,
            "createdAt": "2026-03-12T00:00:00Z",
            "updatedAt": "2026-03-12T00:00:01Z",
        }
    ],
    "totalCount": 1,
    "page": 2,
    "perPage": 5,
}

SNAPSHOT_PAYLOAD_WITHOUT_COMPATIBILITY_TAG = {
    "id": "snap_omitted",
    "snapshotName": "snapshot-omitted",
    "namespace": "team_1",
    "imageNamespace": "team_1",
    "imageName": "node",
    "imageId": "img_123",
    "status": "created",
    "metadata": {},
    "uploaded": True,
    "createdAt": "2026-03-12T00:00:00Z",
    "updatedAt": "2026-03-12T00:00:01Z",
}

PROCESS_RESULT_PAYLOAD = {
    "result": {
        "id": "proc_1",
        "status": "exited",
        "exitCode": 0,
        "stdout": "",
        "stderr": "",
        "startedAt": 1,
        "completedAt": 2,
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
        "exitCode": None,
        "startedAt": 1,
        "completedAt": None,
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

WRITE_FILE_PAYLOAD = {
    "files": [
        {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "type": "file",
        }
    ]
}

EXPOSE_PAYLOAD = {
    "port": 3000,
    "auth": True,
    "url": "https://3000-sbx_123.runtime.example.com/",
    "browserUrl": "https://3000-sbx_123.runtime.example.com/_hb/auth?grant=test&next=%2F",
    "browserUrlExpiresAt": "2026-03-12T02:00:00Z",
}

UNEXPOSE_PAYLOAD = {
    "port": 3000,
    "exposed": False,
}

NETWORK_UPDATE_PAYLOAD = {
    "network": {
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1"],
        "denyOut": ["0.0.0.0/0"],
    }
}

IMAGE_BUILD_RECORD = {
    "id": "build-123",
    "teamId": "team_1",
    "userId": "user_1",
    "namespace": "team_1",
    "imageName": "custom_node",
    "imageId": "img_123",
    "status": "upload_verified",
    "inputBucket": "bucket",
    "inputKey": "input/key",
    "inputSha256": "abc123",
    "inputSizeBytes": 123,
    "outputBucket": "out",
    "outputKey": "output/key",
    "vmId": "vm_123",
    "errorCode": "",
    "errorMessage": "",
    "metadata": {},
    "completedAt": None,
    "createdAt": "2026-03-12T00:00:00Z",
    "updatedAt": "2026-03-12T00:00:01Z",
}

IMAGE_BUILD_CREATE_PAYLOAD = {
    "build": {
        **IMAGE_BUILD_RECORD,
        "status": "awaiting_upload",
        "imageId": "",
    },
    "upload": {
        "url": "https://upload.example.com/rootfs",
        "method": "PUT",
        "headers": {"x-upload": "yes"},
        "objectKey": "input/key",
        "expiresInSeconds": 900,
        "maxUploadBytes": 1000,
    },
}

IMAGE_BUILD_PAYLOAD = {
    "build": IMAGE_BUILD_RECORD,
}

SERVER_IMAGE_BUILD_STATUSES = (
    "awaiting_upload",
    "upload_verified",
    "dispatching",
    "building",
    "verifying",
    "completed",
    "failed",
    "canceled",
)

IMAGE_BUILD_LIST_PAYLOAD = {
    "builds": [
        {
            **IMAGE_BUILD_RECORD,
            "id": f"build-{index}",
            "status": status,
        }
        for index, status in enumerate(SERVER_IMAGE_BUILD_STATUSES)
    ]
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
        elif url.endswith("/images/builds/reuse"):
            payload = {"hit": True, "build": IMAGE_BUILD_RECORD}
        elif url.endswith("/images/builds"):
            payload = (
                IMAGE_BUILD_LIST_PAYLOAD
                if method == "GET"
                else IMAGE_BUILD_CREATE_PAYLOAD
            )
        elif "/images/builds/" in url:
            payload = IMAGE_BUILD_PAYLOAD
        elif "/images/" in url:
            payload = (
                {
                    "deleted": True,
                    "id": "img_123",
                    "imageName": "custom_node",
                    "uploaded": True,
                }
                if method == "DELETE"
                else IMAGE_LIST_PAYLOAD
            )
        elif url.endswith("/images"):
            payload = IMAGE_LIST_PAYLOAD
        elif url.endswith("/snapshots"):
            payload = SNAPSHOT_LIST_PAYLOAD
        elif "/snapshots/" in url:
            payload = (
                {"deleted": True}
                if method == "DELETE"
                else {"snapshot": SNAPSHOT_LIST_PAYLOAD["snapshots"][0]}
            )
        elif url.endswith("/sandbox"):
            payload = SANDBOX_DETAIL_PAYLOAD
        elif url.endswith("/network"):
            payload = NETWORK_UPDATE_PAYLOAD
        elif url.endswith("/expose"):
            payload = EXPOSE_PAYLOAD
        elif url.endswith("/unexpose"):
            payload = UNEXPOSE_PAYLOAD
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
        if path == "/sandbox/files/write":
            return WRITE_FILE_PAYLOAD
        if path == "/sandbox/files/upload":
            return {
                "path": params["path"],
                "bytesWritten": -1,
            }
        if path == "/sandbox/files/move":
            return MOVE_FILE_PAYLOAD
        raise AssertionError(f"Unexpected request path: {path}")

    def request_bytes(self, path, *, method="GET", params=None, headers=None):
        self.calls.append(
            {
                "path": path,
                "method": method,
                "params": params,
                "headers": headers,
                "bytes": True,
            }
        )
        if path == "/sandbox/files/download":
            return b"downloaded"
        raise AssertionError(f"Unexpected request path: {path}")

    def stream_bytes(
        self,
        path,
        *,
        method="GET",
        params=None,
        headers=None,
        chunk_size=65536,
    ):
        self.calls.append(
            {
                "path": path,
                "method": method,
                "params": params,
                "headers": headers,
                "chunk_size": chunk_size,
                "stream": True,
            }
        )
        if path == "/sandbox/files/download":
            return iter([b"down", b"loaded"])
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

    async def request_bytes(self, path, *, method="GET", params=None, headers=None):
        return super().request_bytes(
            path,
            method=method,
            params=params,
            headers=headers,
        )

    async def stream_bytes(
        self,
        path,
        *,
        method="GET",
        params=None,
        headers=None,
        chunk_size=65536,
    ):
        for chunk in super().stream_bytes(
            path,
            method=method,
            params=params,
            headers=headers,
            chunk_size=chunk_size,
        ):
            yield chunk


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
        elif url.endswith("/images/builds/reuse"):
            payload = {"hit": True, "build": IMAGE_BUILD_RECORD}
        elif url.endswith("/images/builds"):
            payload = (
                IMAGE_BUILD_LIST_PAYLOAD
                if method == "GET"
                else IMAGE_BUILD_CREATE_PAYLOAD
            )
        elif "/images/builds/" in url:
            payload = IMAGE_BUILD_PAYLOAD
        elif "/images/" in url:
            payload = (
                {
                    "deleted": True,
                    "id": "img_123",
                    "imageName": "custom_node",
                    "uploaded": True,
                }
                if method == "DELETE"
                else IMAGE_LIST_PAYLOAD
            )
        elif url.endswith("/images"):
            payload = IMAGE_LIST_PAYLOAD
        elif url.endswith("/snapshots"):
            payload = SNAPSHOT_LIST_PAYLOAD
        elif "/snapshots/" in url:
            payload = (
                {"deleted": True}
                if method == "DELETE"
                else {"snapshot": SNAPSHOT_LIST_PAYLOAD["snapshots"][0]}
            )
        elif url.endswith("/sandbox"):
            payload = SANDBOX_DETAIL_PAYLOAD
        elif url.endswith("/network"):
            payload = NETWORK_UPDATE_PAYLOAD
        elif url.endswith("/expose"):
            payload = EXPOSE_PAYLOAD
        elif url.endswith("/unexpose"):
            payload = UNEXPOSE_PAYLOAD
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
        start=100,
        end=200,
        search="sandbox",
    ).model_dump(by_alias=True, exclude_none=True) == {
        "status": "active",
        "page": 2,
        "limit": 5,
        "start": 100,
        "end": 200,
        "search": "sandbox",
    }

    assert CreateSandboxParams(
        image_name="node",
        image_id="img-id",
        cpu=4,
        memory_mib=4096,
        disk_mib=8192,
        enable_recording=True,
        exposed_ports=[SandboxExposeParams(port=3000, auth=True)],
        mounts={
            "/workspace/cache": SandboxVolumeMount(
                id="2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
                type="rw",
                shared=True,
            )
        },
        timeout_minutes=15,
        allow_internet_access=False,
        allow_out=["1.1.1.1", "example.com"],
        deny_out=["0.0.0.0/0"],
    ).model_dump(by_alias=True, exclude_none=True) == {
        "imageName": "node",
        "imageId": "img-id",
        "vcpus": 4,
        "memMiB": 4096,
        "diskSizeMiB": 8192,
        "enableRecording": True,
        "exposedPorts": [{"port": 3000, "auth": True}],
        "mounts": {
            "/workspace/cache": {
                "id": "2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
                "type": "rw",
                "shared": True,
            }
        },
        "timeoutMinutes": 15,
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1", "example.com"],
        "denyOut": ["0.0.0.0/0"],
    }

    assert SandboxNetworkPolicy(
        allow_internet_access=True,
        allow_out=[],
        deny_out=[],
    ).model_dump(by_alias=True, exclude_none=True) == {
        "allowInternetAccess": True,
        "allowOut": [],
        "denyOut": [],
    }
    assert SandboxNetworkPolicy(allow_internet_access=True).model_dump(
        by_alias=True, exclude_none=True
    ) == {"allowInternetAccess": True, "allowOut": [], "denyOut": []}
    assert SandboxNetworkPolicy(allow_internet_access=True).model_dump(
        by_alias=True, exclude_none=True, exclude_unset=True
    ) == {"allowInternetAccess": True}

    assert SandboxImageListParams(
        page=2,
        limit=5,
        search="node",
        sources=["registry", "uploaded"],
    ).model_dump(by_alias=True, exclude_none=True) == {
        "page": 2,
        "limit": 5,
        "search": "node",
        "source": ["registry", "uploaded"],
    }

    assert CreateSandboxImageBuildParams(
        image_name="custom_node",
        input_sha256="abc123",
        input_size_bytes=123,
        input_format="rootfs_export_tar_gz",
        source_platform="linux/amd64",
        image_config_user="node",
        image_init=SandboxImageInit(
            env={"NODE_ENV": "production"},
            args=["node", "server.js"],
        ),
    ).model_dump(by_alias=True, exclude_none=True) == {
        "imageName": "custom_node",
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
        "inputFormat": "rootfs_export_tar_gz",
        "sourcePlatform": "linux/amd64",
        "imageConfigUser": "node",
        "imageInit": {
            "env": {"NODE_ENV": "production"},
            "args": ["node", "server.js"],
        },
    }

    assert CompleteSandboxImageBuildParams(
        input_sha256="abc123",
        input_size_bytes=123,
        input_format="rootfs_export_tar_gz",
    ).model_dump(by_alias=True, exclude_none=True) == {
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
        "inputFormat": "rootfs_export_tar_gz",
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
        run_as="root",
        use_shell=True,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
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

    assert SandboxSnapshotListParams(
        status=["created", "failed"],
        limit=10,
        image_name="node",
        search="snap",
        page=2,
    ).model_dump(by_alias=True, exclude_none=True) == {
        "status": ["created", "failed"],
        "limit": 10,
        "imageName": "node",
        "search": "snap",
        "page": 2,
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


def test_sandbox_process_models_accept_current_camel_case_wire_keys():
    summary = SandboxProcessSummary(**PROCESS_SUMMARY_PAYLOAD["process"])
    result = SandboxProcessResult(**PROCESS_RESULT_PAYLOAD["result"])

    assert summary.exit_code is None
    assert summary.started_at == 1
    assert summary.completed_at is None
    assert result.exit_code == 0
    assert result.started_at == 1
    assert result.completed_at == 2


def test_sync_sandbox_image_build_manager_uses_expected_wire_keys():
    client = FakeSyncClient()
    manager = SandboxManager(client)

    created = manager.create_image_build(
        CreateSandboxImageBuildParams(
            image_name="custom_node",
            input_sha256="abc123",
            input_size_bytes=123,
            image_config_user="node",
            image_init=SandboxImageInit(args=["node", "server.js"]),
        )
    )
    build = manager.get_image_build("build-123")
    completed = manager.complete_image_build(
        "build-123",
        CompleteSandboxImageBuildParams(
            input_sha256="abc123",
            input_size_bytes=123,
        ),
    )
    canceled = manager.cancel_image_build("build-123")

    create_call = client.transport.client.calls[0]
    get_call = client.transport.client.calls[1]
    complete_call = client.transport.client.calls[2]
    cancel_call = client.transport.client.calls[3]

    assert create_call["method"] == "POST"
    assert create_call["url"].endswith("/images/builds")
    assert create_call["json"] == {
        "imageName": "custom_node",
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
        "imageConfigUser": "node",
        "imageInit": {"args": ["node", "server.js"]},
    }
    assert created.build.status == "awaiting_upload"
    assert created.upload.url == "https://upload.example.com/rootfs"
    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/images/builds/build-123")
    assert complete_call["method"] == "POST"
    assert complete_call["url"].endswith("/images/builds/build-123/complete")
    assert complete_call["json"] == {
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
    }
    assert cancel_call["method"] == "POST"
    assert cancel_call["url"].endswith("/images/builds/build-123/cancel")
    assert build.image_name == "custom_node"
    assert completed.status == "upload_verified"
    assert canceled.status == "upload_verified"


def test_sync_sandbox_image_build_reuse_uses_expected_wire_keys():
    client = FakeSyncClient()
    manager = SandboxManager(client)

    result = manager.reuse_docker_image(
        ReuseSandboxDockerImageParams(
            image_name="custom_node",
            source_image_digest="sha256:" + "a" * 64,
            source_platform="linux/amd64",
            image_config_user="node",
            image_init=SandboxImageInit(working_dir="/app"),
        )
    )

    assert client.transport.client.calls[0] == {
        "method": "POST",
        "url": "https://api.example.com/images/builds/reuse",
        "params": {},
        "json": {
            "imageName": "custom_node",
            "sourceImageDigest": "sha256:" + "a" * 64,
            "sourcePlatform": "linux/amd64",
            "imageConfigUser": "node",
            "imageInit": {"workingDir": "/app"},
        },
    }
    assert result.hit is True
    assert result.build.image_name == "custom_node"


@pytest.mark.parametrize("use_legacy_model", [False, True])
def test_sync_start_from_snapshot_uses_snapshot_only_payload(use_legacy_model):
    client = FakeSyncClient()
    params_data = {
        "snapshot_name": "snapshot-1",
        "snapshot_id": "snap_123",
        "timeout_minutes": 15,
    }
    params = (
        StartSandboxFromSnapshotParams(**params_data)
        if use_legacy_model
        else params_data
    )

    sandbox = SandboxManager(client).start_from_snapshot(params)

    assert sandbox.id == "sbx_123"
    assert client.transport.client.calls[0]["json"] == {
        "snapshotName": "snapshot-1",
        "snapshotId": "snap_123",
        "timeoutMinutes": 15,
    }


@pytest.mark.parametrize("use_legacy_model", [False, True])
def test_sync_sandbox_snapshot_and_image_build_list_contract(use_legacy_model):
    client = FakeSyncClient()
    manager = SandboxManager(client)
    params_data = {"status": "dispatching", "limit": 25}
    params = (
        SandboxImageBuildListParams(**params_data) if use_legacy_model else params_data
    )

    builds = manager.list_image_builds(params)
    snapshot = manager.get_snapshot("snapshot-1")
    deleted = manager.delete_snapshot("snapshot-1")
    deleted_image = manager.delete_image("custom_node")

    list_call, get_call, delete_call, delete_image_call = client.transport.client.calls
    assert list_call == {
        "method": "GET",
        "url": "https://api.example.com/images/builds",
        "params": params_data,
        "json": None,
    }
    assert [build.status for build in builds.builds] == list(
        SERVER_IMAGE_BUILD_STATUSES
    )
    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/snapshots/snapshot-1")
    assert snapshot.snapshot_name == "snapshot-1"
    assert snapshot.vcpus == 2
    assert snapshot.mem_mib == 2048
    assert snapshot.disk_size_mib == 8192
    assert delete_call["method"] == "DELETE"
    assert delete_call["url"].endswith("/snapshots/snapshot-1")
    assert deleted.deleted is True
    assert delete_image_call["method"] == "DELETE"
    assert delete_image_call["url"].endswith("/images/custom_node")
    assert deleted_image.deleted is True
    assert deleted_image.id == "img_123"
    assert deleted_image.image_name == "custom_node"
    assert deleted_image.uploaded is True


@pytest.mark.parametrize(
    "params",
    [
        {
            "image_name": "custom_node",
            "input_sha256": "abc123",
            "input_size_bytes": 123,
        },
        CreateSandboxImageBuildParams(
            image_name="custom_node",
            input_sha256="abc123",
            input_size_bytes=123,
        ),
    ],
)
def test_sync_image_build_omits_unspecified_fields_for_dicts_and_legacy_models(
    params,
):
    client = FakeSyncClient()
    manager = SandboxManager(client)

    manager.create_image_build(params)
    complete_params = (
        {
            "input_sha256": "abc123",
            "input_size_bytes": 123,
        }
        if isinstance(params, dict)
        else CompleteSandboxImageBuildParams(
            input_sha256="abc123",
            input_size_bytes=123,
        )
    )
    manager.complete_image_build("build-123", complete_params)

    assert client.transport.client.calls[0]["json"] == {
        "imageName": "custom_node",
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
    }
    assert client.transport.client.calls[1]["json"] == {
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
    }


def test_sync_sandbox_control_manager_uses_expected_wire_keys():
    client = FakeSyncClient()
    manager = SandboxManager(client)
    runtime = type("Runtime", (), {"base_url": "https://runtime.example.com"})()

    listed = manager.list(
        SandboxListParams(
            status="active",
            page=2,
            limit=5,
            start=100,
            end=200,
            search="sandbox",
        )
    )
    images = manager.list_images(
        SandboxImageListParams(
            page=2,
            limit=5,
            search="node",
            sources=["registry", "uploaded"],
        )
    )
    snapshots = manager.list_snapshots(
        SandboxSnapshotListParams(
            status=["created", "failed"],
            limit=10,
            image_name="node",
            search="snap",
            page=2,
        )
    )
    sandbox = manager.create(
        CreateSandboxParams(
            image_name="node",
            image_id="img-id",
            cpu=4,
            memory_mib=4096,
            disk_mib=8192,
            enable_recording=True,
            exposed_ports=[SandboxExposeParams(port=3000, auth=True)],
            mounts={
                "/workspace/cache": SandboxVolumeMount(
                    id="2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
                    type="rw",
                    shared=True,
                )
            },
            timeout_minutes=15,
            allow_internet_access=False,
            allow_out=["1.1.1.1", "example.com"],
            deny_out=["0.0.0.0/0"],
        )
    )
    manager.create_memory_snapshot(
        "sbx_123",
        SandboxMemorySnapshotParams(snapshot_name="snap"),
    )
    network = sandbox.update_network(
        SandboxNetworkPolicy(
            allow_internet_access=False,
            allow_out=["1.1.1.1"],
            deny_out=["0.0.0.0/0"],
        )
    )
    exposed = manager.expose(
        "sbx_123",
        SandboxExposeParams(port=3000, auth=True),
        runtime=runtime,
    )
    unexposed = manager.unexpose("sbx_123", 3000)

    list_call = client.transport.client.calls[0]
    images_call = client.transport.client.calls[1]
    snapshots_call = client.transport.client.calls[2]
    create_call = client.transport.client.calls[3]
    snapshot_call = client.transport.client.calls[4]
    network_call = client.transport.client.calls[5]
    expose_call = client.transport.client.calls[6]
    unexpose_call = client.transport.client.calls[7]

    assert list_call["params"] == {
        "status": "active",
        "page": 2,
        "limit": 5,
        "start": 100,
        "end": 200,
        "search": "sandbox",
    }
    assert listed.total_count == 1
    assert listed.page == 2
    assert listed.per_page == 5
    assert images_call["url"].endswith("/images")
    assert images_call["params"] == {
        "page": 2,
        "limit": 5,
        "search": "node",
        "source": ["registry", "uploaded"],
    }
    assert images.images[0].image_name == "node"
    assert images.images[0].source == "registry"
    assert images.images[0].image_init is not None
    assert images.images[0].image_init.args == ["node", "server.js"]
    assert images.total_count == 1
    assert images.page == 2
    assert images.per_page == 5
    assert snapshots_call["url"].endswith("/snapshots")
    assert snapshots_call["params"] == {
        "status": ["created", "failed"],
        "limit": 10,
        "imageName": "node",
        "search": "snap",
        "page": 2,
    }
    assert snapshots.snapshots[0].compatibility_tag is None
    assert snapshots.total_count == 1
    assert snapshots.page == 2
    assert snapshots.per_page == 5
    assert create_call["json"] == {
        "imageName": "node",
        "imageId": "img-id",
        "vcpus": 4,
        "memMiB": 4096,
        "diskSizeMiB": 8192,
        "enableRecording": True,
        "exposedPorts": [{"port": 3000, "auth": True}],
        "mounts": {
            "/workspace/cache": {
                "id": "2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
                "type": "rw",
                "shared": True,
            }
        },
        "timeoutMinutes": 15,
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1", "example.com"],
        "denyOut": ["0.0.0.0/0"],
    }
    assert snapshot_call["json"] == {
        "snapshotName": "snap",
    }
    assert network_call["method"] == "PUT"
    assert network_call["url"].endswith("/sandbox/sbx_123/network")
    assert network_call["json"] == {
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1"],
        "denyOut": ["0.0.0.0/0"],
    }
    assert sandbox.cpu == 2
    assert sandbox.memory_mib == 2048
    assert sandbox.disk_mib == 8192
    assert sandbox.network is not None
    assert sandbox.network.allow_out == ["1.1.1.1"]
    assert sandbox.exposed_ports[0].browser_url is not None
    assert network.network.allow_internet_access is False
    assert sandbox.get_exposed_url(3000) == "https://3000-sbx_123.runtime.example.com/"
    assert expose_call["json"] == {"port": 3000, "auth": True}
    assert exposed.browser_url is not None
    assert expose_call["url"].endswith("/sandbox/sbx_123/expose")
    assert isinstance(unexposed, SandboxUnexposeResult)
    assert unexpose_call["json"] == {"port": 3000}
    assert unexpose_call["url"].endswith("/sandbox/sbx_123/unexpose")


def test_sync_sandbox_update_network_omits_only_unset_lists():
    client = FakeSyncClient()
    manager = SandboxManager(client)
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    sandbox.update_network(SandboxNetworkPolicy(allow_internet_access=True))
    sandbox.update_network(
        SandboxNetworkPolicy(
            allow_internet_access=True,
            allow_out=[],
            deny_out=[],
        )
    )

    preserve_call = client.transport.client.calls[0]
    clear_call = client.transport.client.calls[1]
    assert preserve_call["json"] == {"allowInternetAccess": True}
    assert clear_call["json"] == {
        "allowInternetAccess": True,
        "allowOut": [],
        "denyOut": [],
    }


def test_snapshot_summary_allows_missing_compatibility_tag():
    snapshot = SandboxSnapshotSummary(**SNAPSHOT_PAYLOAD_WITHOUT_COMPATIBILITY_TAG)

    assert snapshot.compatibility_tag is None


def test_sandbox_models_accept_close_error_status():
    sandbox = SandboxDetail(**{**SANDBOX_DETAIL_PAYLOAD, "status": "close-error"})
    params = SandboxListParams(status="close-error")

    assert sandbox.status == "close-error"
    assert params.status == "close-error"


def test_sandbox_response_and_handles_expose_timeout_minutes():
    detail = SandboxDetail(**SANDBOX_DETAIL_PAYLOAD)
    sync_handle = SandboxHandle(SandboxManager(FakeSyncClient()), detail)
    async_handle = AsyncSandboxHandle(AsyncSandboxManager(FakeAsyncClient()), detail)

    assert detail.timeout_minutes == 30
    assert sync_handle.timeout_minutes == 30
    assert async_handle.timeout_minutes == 30


def test_sync_close_error_sandbox_is_unavailable_at_runtime():
    manager = SandboxManager(FakeSyncClient())
    sandbox = SandboxHandle(
        manager,
        SandboxDetail(**{**SANDBOX_DETAIL_PAYLOAD, "status": "close-error"}),
    )

    with pytest.raises(HyperbrowserError, match="Sandbox sbx_123 is not running"):
        sandbox.connect()


@pytest.mark.anyio
async def test_async_close_error_sandbox_is_unavailable_at_runtime():
    manager = AsyncSandboxManager(FakeAsyncClient())
    sandbox = AsyncSandboxHandle(
        manager,
        SandboxDetail(**{**SANDBOX_DETAIL_PAYLOAD, "status": "close-error"}),
    )

    with pytest.raises(HyperbrowserError, match="Sandbox sbx_123 is not running"):
        await sandbox.connect()


def test_image_build_list_params_leave_numeric_validation_to_server():
    params = SandboxImageBuildListParams(limit=-1)

    assert params.limit == -1


def test_build_sandbox_exposed_url_uses_runtime_base_path_session_id():
    runtime = SimpleNamespace(
        host="https://runtime.example.com",
        base_url="https://runtime.example.com/sandbox/sbx_123",
    )

    assert (
        _build_sandbox_exposed_url(runtime, 3000)
        == "https://3000-sbx_123.runtime.example.com/"
    )


def test_build_sandbox_exposed_url_uses_session_id_from_runtime_host_path():
    runtime = SimpleNamespace(
        host="https://runtime.example.com/sandbox/sbx_123",
        base_url="https://runtime.example.com",
    )

    assert (
        _build_sandbox_exposed_url(runtime, 3000)
        == "https://3000-sbx_123.runtime.example.com/"
    )


def test_sync_sandbox_runtime_apis_use_expected_wire_keys():
    transport = RecordingTransport()

    processes = SandboxProcessesApi(transport)
    process_input = SandboxExecParams(
        command="echo",
        args=["hi world"],
        timeout_ms=500,
        timeout_sec=7,
        run_as="root",
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
    files.write(
        [
            SandboxFileWriteEntry(
                path="/tmp/a.txt",
                data="aGVsbG8=",
                encoding="base64",
                append=True,
                mode="600",
            )
        ]
    )
    files.get_watch("watch_1", include_events=True)
    files.upload_url("/tmp/file.txt", expires_in_seconds=60, one_time=True)
    files.download_url("/tmp/file.txt", expires_in_seconds=30, one_time=False)
    files.move(
        source="/tmp/source.txt",
        destination="/tmp/destination.txt",
        overwrite=True,
    )
    upload_result = files.upload_stream(
        "/tmp/upload.bin",
        io.BytesIO(b"abcdef"),
        content_length=6,
        chunk_size=2,
    )
    downloaded = b"".join(files.download_stream("/tmp/file.txt", chunk_size=4))

    assert transport.calls[0]["json_body"] == {
        "command": "echo 'hi world'",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
    }
    assert transport.calls[1]["json_body"] == {
        "command": "echo 'hi world'",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
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
    assert transport.calls[7]["json_body"] == {
        "files": [
            {
                "path": "/tmp/a.txt",
                "data": "aGVsbG8=",
                "encoding": "base64",
                "append": True,
                "mode": "600",
            }
        ]
    }
    assert transport.calls[8]["params"] == {"includeEvents": True}
    assert transport.calls[9]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 60,
        "oneTime": True,
    }
    assert transport.calls[10]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 30,
        "oneTime": False,
    }
    assert transport.calls[11]["json_body"] == {
        "from": "/tmp/source.txt",
        "to": "/tmp/destination.txt",
        "overwrite": True,
    }
    assert transport.calls[12]["path"] == "/sandbox/files/upload"
    assert transport.calls[12]["params"] == {"path": "/tmp/upload.bin"}
    assert transport.calls[12]["headers"] == {"content-length": "6"}
    assert b"".join(transport.calls[12]["content"]) == b"abcdef"
    assert upload_result.path == "/tmp/upload.bin"
    assert transport.calls[13] == {
        "path": "/sandbox/files/download",
        "method": "GET",
        "params": {"path": "/tmp/file.txt"},
        "headers": None,
        "chunk_size": 4,
        "stream": True,
    }
    assert downloaded == b"downloaded"


def test_sync_sandbox_process_string_calls_support_run_as():
    transport = RecordingTransport()
    processes = SandboxProcessesApi(transport)

    processes.exec(
        "whoami",
        cwd="/tmp",
        env={"FOO": "bar"},
        timeout_ms=500,
        timeout_sec=7,
        run_as="root",
    )
    processes.start(
        "sleep 30",
        cwd="/tmp",
        run_as="root",
    )

    assert transport.calls[0]["json_body"] == {
        "command": "whoami",
        "cwd": "/tmp",
        "env": {"FOO": "bar"},
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
    }
    assert transport.calls[1]["json_body"] == {
        "command": "sleep 30",
        "cwd": "/tmp",
        "runAs": "root",
    }


def test_sync_sandbox_handle_exec_string_call_supports_run_as(monkeypatch):
    manager = SandboxManager(FakeSyncClient())
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))
    calls = []

    def fake_exec(input, **kwargs):
        calls.append((input, kwargs))
        return PROCESS_RESULT_PAYLOAD["result"]

    monkeypatch.setattr(sandbox.processes, "exec", fake_exec)

    sandbox.exec("whoami", run_as="root")

    assert calls == [
        (
            "whoami",
            {
                "cwd": None,
                "env": None,
                "timeout_ms": None,
                "timeout_sec": None,
                "run_as": "root",
            },
        )
    ]


@pytest.mark.anyio
async def test_async_sandbox_image_build_manager_uses_expected_wire_keys():
    client = FakeAsyncClient()
    manager = AsyncSandboxManager(client)

    created = await manager.create_image_build(
        CreateSandboxImageBuildParams(
            image_name="custom_node",
            input_sha256="abc123",
            input_size_bytes=123,
            image_config_user="node",
            image_init=SandboxImageInit(args=["node", "server.js"]),
        )
    )
    build = await manager.get_image_build("build-123")
    completed = await manager.complete_image_build(
        "build-123",
        CompleteSandboxImageBuildParams(
            input_sha256="abc123",
            input_size_bytes=123,
        ),
    )
    canceled = await manager.cancel_image_build("build-123")

    create_call = client.transport.client.calls[0]
    get_call = client.transport.client.calls[1]
    complete_call = client.transport.client.calls[2]
    cancel_call = client.transport.client.calls[3]

    assert create_call["method"] == "POST"
    assert create_call["url"].endswith("/images/builds")
    assert create_call["json"] == {
        "imageName": "custom_node",
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
        "imageConfigUser": "node",
        "imageInit": {"args": ["node", "server.js"]},
    }
    assert created.build.status == "awaiting_upload"
    assert created.upload.url == "https://upload.example.com/rootfs"
    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/images/builds/build-123")
    assert complete_call["method"] == "POST"
    assert complete_call["url"].endswith("/images/builds/build-123/complete")
    assert complete_call["json"] == {
        "inputSha256": "abc123",
        "inputSizeBytes": 123,
    }
    assert cancel_call["method"] == "POST"
    assert cancel_call["url"].endswith("/images/builds/build-123/cancel")
    assert build.image_name == "custom_node"
    assert completed.status == "upload_verified"
    assert canceled.status == "upload_verified"


@pytest.mark.anyio
async def test_async_sandbox_image_build_reuse_uses_expected_wire_keys():
    client = FakeAsyncClient()
    manager = AsyncSandboxManager(client)

    result = await manager.reuse_docker_image(
        {
            "image_name": "custom_node",
            "source_image_digest": "sha256:" + "a" * 64,
            "source_platform": "linux/amd64",
        }
    )

    assert client.transport.client.calls[0] == {
        "method": "POST",
        "url": "https://api.example.com/images/builds/reuse",
        "params": {},
        "json": {
            "imageName": "custom_node",
            "sourceImageDigest": "sha256:" + "a" * 64,
            "sourcePlatform": "linux/amd64",
        },
    }
    assert result.hit is True
    assert result.build.image_name == "custom_node"


@pytest.mark.anyio
@pytest.mark.parametrize("use_legacy_model", [False, True])
async def test_async_start_from_snapshot_uses_snapshot_only_payload(
    use_legacy_model,
):
    client = FakeAsyncClient()
    params_data = {
        "snapshot_name": "snapshot-1",
        "snapshot_id": "snap_123",
        "timeout_minutes": 15,
    }
    params = (
        StartSandboxFromSnapshotParams(**params_data)
        if use_legacy_model
        else params_data
    )

    sandbox = await AsyncSandboxManager(client).start_from_snapshot(params)

    assert sandbox.id == "sbx_123"
    assert client.transport.client.calls[0]["json"] == {
        "snapshotName": "snapshot-1",
        "snapshotId": "snap_123",
        "timeoutMinutes": 15,
    }


@pytest.mark.anyio
@pytest.mark.parametrize("use_legacy_model", [False, True])
async def test_async_sandbox_snapshot_and_image_build_list_contract(
    use_legacy_model,
):
    client = FakeAsyncClient()
    manager = AsyncSandboxManager(client)
    params_data = {"status": "verifying", "limit": 25}
    params = (
        SandboxImageBuildListParams(**params_data) if use_legacy_model else params_data
    )

    builds = await manager.list_image_builds(params)
    snapshot = await manager.get_snapshot("snapshot-1")
    deleted = await manager.delete_snapshot("snapshot-1")
    deleted_image = await manager.delete_image("custom_node")

    list_call, get_call, delete_call, delete_image_call = client.transport.client.calls
    assert list_call == {
        "method": "GET",
        "url": "https://api.example.com/images/builds",
        "params": params_data,
        "json": None,
    }
    assert [build.status for build in builds.builds] == list(
        SERVER_IMAGE_BUILD_STATUSES
    )
    assert get_call["method"] == "GET"
    assert get_call["url"].endswith("/snapshots/snapshot-1")
    assert snapshot.snapshot_name == "snapshot-1"
    assert snapshot.vcpus == 2
    assert snapshot.mem_mib == 2048
    assert snapshot.disk_size_mib == 8192
    assert delete_call["method"] == "DELETE"
    assert delete_call["url"].endswith("/snapshots/snapshot-1")
    assert deleted.deleted is True
    assert delete_image_call["method"] == "DELETE"
    assert delete_image_call["url"].endswith("/images/custom_node")
    assert deleted_image.deleted is True
    assert deleted_image.id == "img_123"
    assert deleted_image.image_name == "custom_node"
    assert deleted_image.uploaded is True


@pytest.mark.anyio
async def test_async_sandbox_control_manager_uses_expected_wire_keys():
    client = FakeAsyncClient()
    manager = AsyncSandboxManager(client)
    runtime = type("Runtime", (), {"base_url": "https://runtime.example.com"})()

    listed = await manager.list(
        SandboxListParams(
            status="active",
            page=2,
            limit=5,
            start=100,
            end=200,
            search="sandbox",
        )
    )
    images = await manager.list_images(
        SandboxImageListParams(
            page=2,
            limit=5,
            search="node",
            sources=["registry", "uploaded"],
        )
    )
    snapshots = await manager.list_snapshots(
        SandboxSnapshotListParams(
            status=["created", "failed"],
            limit=10,
            image_name="node",
            search="snap",
            page=2,
        )
    )
    sandbox = await manager.create(
        CreateSandboxParams(
            image_name="node",
            image_id="img-id",
            cpu=4,
            memory_mib=4096,
            disk_mib=8192,
            enable_recording=True,
            exposed_ports=[SandboxExposeParams(port=3000, auth=True)],
            mounts={
                "/workspace/cache": SandboxVolumeMount(
                    id="2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
                    type="rw",
                    shared=True,
                )
            },
            timeout_minutes=15,
            allow_internet_access=False,
            allow_out=["1.1.1.1", "example.com"],
            deny_out=["0.0.0.0/0"],
        )
    )
    await manager.create_memory_snapshot(
        "sbx_123",
        SandboxMemorySnapshotParams(snapshot_name="snap"),
    )
    network = await sandbox.update_network(
        SandboxNetworkPolicy(
            allow_internet_access=False,
            allow_out=["1.1.1.1"],
            deny_out=["0.0.0.0/0"],
        )
    )
    exposed = await manager.expose(
        "sbx_123",
        SandboxExposeParams(port=3000, auth=True),
        runtime=runtime,
    )
    unexposed = await manager.unexpose("sbx_123", 3000)

    list_call = client.transport.client.calls[0]
    images_call = client.transport.client.calls[1]
    snapshots_call = client.transport.client.calls[2]
    create_call = client.transport.client.calls[3]
    snapshot_call = client.transport.client.calls[4]
    network_call = client.transport.client.calls[5]
    expose_call = client.transport.client.calls[6]
    unexpose_call = client.transport.client.calls[7]

    assert list_call["params"] == {
        "status": "active",
        "page": 2,
        "limit": 5,
        "start": 100,
        "end": 200,
        "search": "sandbox",
    }
    assert listed.total_count == 1
    assert listed.page == 2
    assert listed.per_page == 5
    assert images_call["url"].endswith("/images")
    assert images_call["params"] == {
        "page": 2,
        "limit": 5,
        "search": "node",
        "source": ["registry", "uploaded"],
    }
    assert images.images[0].image_name == "node"
    assert images.images[0].source == "registry"
    assert images.images[0].image_init is not None
    assert images.images[0].image_init.args == ["node", "server.js"]
    assert images.total_count == 1
    assert images.page == 2
    assert images.per_page == 5
    assert snapshots_call["url"].endswith("/snapshots")
    assert snapshots_call["params"] == {
        "status": ["created", "failed"],
        "limit": 10,
        "imageName": "node",
        "search": "snap",
        "page": 2,
    }
    assert snapshots.snapshots[0].compatibility_tag is None
    assert snapshots.total_count == 1
    assert snapshots.page == 2
    assert snapshots.per_page == 5
    assert create_call["json"] == {
        "imageName": "node",
        "imageId": "img-id",
        "vcpus": 4,
        "memMiB": 4096,
        "diskSizeMiB": 8192,
        "enableRecording": True,
        "exposedPorts": [{"port": 3000, "auth": True}],
        "mounts": {
            "/workspace/cache": {
                "id": "2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d",
                "type": "rw",
                "shared": True,
            }
        },
        "timeoutMinutes": 15,
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1", "example.com"],
        "denyOut": ["0.0.0.0/0"],
    }
    assert snapshot_call["json"] == {
        "snapshotName": "snap",
    }
    assert network_call["method"] == "PUT"
    assert network_call["url"].endswith("/sandbox/sbx_123/network")
    assert network_call["json"] == {
        "allowInternetAccess": False,
        "allowOut": ["1.1.1.1"],
        "denyOut": ["0.0.0.0/0"],
    }
    assert sandbox.cpu == 2
    assert sandbox.memory_mib == 2048
    assert sandbox.disk_mib == 8192
    assert sandbox.network is not None
    assert sandbox.network.allow_out == ["1.1.1.1"]
    assert sandbox.exposed_ports[0].browser_url is not None
    assert network.network.allow_internet_access is False
    assert sandbox.get_exposed_url(3000) == "https://3000-sbx_123.runtime.example.com/"
    assert expose_call["json"] == {"port": 3000, "auth": True}
    assert exposed.browser_url is not None
    assert isinstance(unexposed, SandboxUnexposeResult)
    assert unexpose_call["json"] == {"port": 3000}


@pytest.mark.anyio
async def test_async_sandbox_update_network_omits_only_unset_lists():
    client = FakeAsyncClient()
    manager = AsyncSandboxManager(client)
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    await sandbox.update_network(SandboxNetworkPolicy(allow_internet_access=True))
    await sandbox.update_network(
        SandboxNetworkPolicy(
            allow_internet_access=True,
            allow_out=[],
            deny_out=[],
        )
    )

    preserve_call = client.transport.client.calls[0]
    clear_call = client.transport.client.calls[1]
    assert preserve_call["json"] == {"allowInternetAccess": True}
    assert clear_call["json"] == {
        "allowInternetAccess": True,
        "allowOut": [],
        "denyOut": [],
    }


@pytest.mark.anyio
async def test_async_sandbox_runtime_apis_use_expected_wire_keys():
    transport = AsyncRecordingTransport()

    processes = AsyncSandboxProcessesApi(transport)
    process_input = SandboxExecParams(
        command="echo",
        args=["hi world"],
        timeout_ms=500,
        timeout_sec=7,
        run_as="root",
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
    await files.write(
        [
            SandboxFileWriteEntry(
                path="/tmp/a.txt",
                data="aGVsbG8=",
                encoding="base64",
                append=True,
                mode="600",
            )
        ]
    )
    await files.get_watch("watch_1", include_events=True)
    await files.upload_url("/tmp/file.txt", expires_in_seconds=60, one_time=True)
    await files.download_url("/tmp/file.txt", expires_in_seconds=30, one_time=False)
    await files.move(
        source="/tmp/source.txt",
        destination="/tmp/destination.txt",
        overwrite=True,
    )
    upload_result = await files.upload_stream(
        "/tmp/upload.bin",
        io.BytesIO(b"abcdef"),
        content_length=6,
        chunk_size=2,
    )
    chunks = []
    async for chunk in files.download_stream("/tmp/file.txt", chunk_size=4):
        chunks.append(chunk)
    downloaded = b"".join(chunks)

    assert transport.calls[0]["json_body"] == {
        "command": "echo 'hi world'",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
    }
    assert transport.calls[1]["json_body"] == {
        "command": "echo 'hi world'",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
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
    assert transport.calls[7]["json_body"] == {
        "files": [
            {
                "path": "/tmp/a.txt",
                "data": "aGVsbG8=",
                "encoding": "base64",
                "append": True,
                "mode": "600",
            }
        ]
    }
    assert transport.calls[8]["params"] == {"includeEvents": True}
    assert transport.calls[9]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 60,
        "oneTime": True,
    }
    assert transport.calls[10]["json_body"] == {
        "path": "/tmp/file.txt",
        "expiresInSeconds": 30,
        "oneTime": False,
    }
    assert transport.calls[11]["json_body"] == {
        "from": "/tmp/source.txt",
        "to": "/tmp/destination.txt",
        "overwrite": True,
    }
    assert transport.calls[12]["path"] == "/sandbox/files/upload"
    assert transport.calls[12]["params"] == {"path": "/tmp/upload.bin"}
    assert transport.calls[12]["headers"] == {"content-length": "6"}
    async_upload_chunks = []
    async for chunk in transport.calls[12]["content"]:
        async_upload_chunks.append(chunk)
    assert b"".join(async_upload_chunks) == b"abcdef"
    assert upload_result.path == "/tmp/upload.bin"
    assert transport.calls[13] == {
        "path": "/sandbox/files/download",
        "method": "GET",
        "params": {"path": "/tmp/file.txt"},
        "headers": None,
        "chunk_size": 4,
        "stream": True,
    }
    assert downloaded == b"downloaded"


@pytest.mark.anyio
async def test_async_sandbox_process_string_calls_support_run_as():
    transport = AsyncRecordingTransport()
    processes = AsyncSandboxProcessesApi(transport)

    await processes.exec(
        "whoami",
        cwd="/tmp",
        env={"FOO": "bar"},
        timeout_ms=500,
        timeout_sec=7,
        run_as="root",
    )
    await processes.start(
        "sleep 30",
        cwd="/tmp",
        run_as="root",
    )

    assert transport.calls[0]["json_body"] == {
        "command": "whoami",
        "cwd": "/tmp",
        "env": {"FOO": "bar"},
        "timeoutMs": 500,
        "timeout_sec": 7,
        "runAs": "root",
    }
    assert transport.calls[1]["json_body"] == {
        "command": "sleep 30",
        "cwd": "/tmp",
        "runAs": "root",
    }


def test_sync_terminal_attach_includes_cursor(monkeypatch):
    captured = {}

    class DummyTarget:
        url = (
            "wss://runtime.example.com/sandbox/pty/pty_1/ws?sessionId=sbx_123&cursor=7"
        )
        host_header = None
        connect_host = None
        connect_port = None

    def fake_target(base_url, path, runtime_proxy_override):
        captured["path"] = path
        return DummyTarget()

    def fake_connect(url, additional_headers=None, open_timeout=None, **kwargs):
        captured["url"] = url
        return object()

    monkeypatch.setattr(
        sync_terminal_module, "to_websocket_transport_target", fake_target
    )
    monkeypatch.setattr(sync_terminal_module, "sync_ws_connect", fake_connect)

    handle = sync_terminal_module.SandboxTerminalHandle(
        transport=type("Transport", (), {"_timeout": 30})(),
        get_connection_info=lambda: type(
            "Conn",
            (),
            {
                "sandbox_id": "sbx_123",
                "base_url": "https://runtime.example.com",
                "token": "tok",
            },
        )(),
        status=sync_terminal_module._normalize_terminal_status(PTY_PAYLOAD["pty"]),
    )

    handle.attach(cursor=7)

    assert "cursor=7" in captured["path"]
    assert "cursor=7" in captured["url"]


@pytest.mark.anyio
async def test_async_terminal_attach_includes_cursor(monkeypatch):
    captured = {}

    class DummyTarget:
        url = (
            "wss://runtime.example.com/sandbox/pty/pty_1/ws?sessionId=sbx_123&cursor=7"
        )
        host_header = None
        connect_host = None
        connect_port = None

    def fake_target(base_url, path, runtime_proxy_override):
        captured["path"] = path
        return DummyTarget()

    async def fake_connect(url, additional_headers=None, open_timeout=None, **kwargs):
        captured["url"] = url
        return object()

    monkeypatch.setattr(
        async_terminal_module, "to_websocket_transport_target", fake_target
    )
    monkeypatch.setattr(async_terminal_module, "async_ws_connect", fake_connect)

    async def get_connection_info():
        return type(
            "Conn",
            (),
            {
                "sandbox_id": "sbx_123",
                "base_url": "https://runtime.example.com",
                "token": "tok",
            },
        )()

    handle = async_terminal_module.SandboxTerminalHandle(
        transport=type("Transport", (), {"_timeout": 30})(),
        get_connection_info=get_connection_info,
        status=async_terminal_module._normalize_terminal_status(PTY_PAYLOAD["pty"]),
    )

    await handle.attach(cursor=7)

    assert "cursor=7" in captured["path"]
    assert "cursor=7" in captured["url"]
