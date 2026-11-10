import inspect
from types import SimpleNamespace

import httpx
import pytest

import hyperbrowser
import hyperbrowser.image_builds as image_builds
import hyperbrowser.models as models
import hyperbrowser.tools as tools
import hyperbrowser.types.session as session_types
from hyperbrowser import AsyncHyperbrowser, Hyperbrowser, HyperbrowserError
from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxHandle as AsyncSandboxHandle,
)
from hyperbrowser.client.managers.sandboxes.image_build import (
    DockerCommandError,
    _run_command_result,
)
from hyperbrowser.client.managers.sync_manager.sandbox import SandboxHandle
from hyperbrowser.models.agents.browser_use import (
    BrowserUseTaskData,
    BrowserUseTaskResponse,
)
from hyperbrowser.models.sandbox import SandboxDetail
from hyperbrowser.models.session import (
    CreateSessionParams,
    GetActiveSessionsCountResponse,
    SessionLaunchState,
)
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.base import TransportStrategy
from hyperbrowser.transport.sync import SyncTransport
from tests.test_sandbox_wire_contract import (
    SANDBOX_DETAIL_PAYLOAD,
    SNAPSHOT_LIST_PAYLOAD,
    SNAPSHOT_RESULT_PAYLOAD,
)


def test_top_level_and_submodule_exports():
    assert hyperbrowser.HyperbrowserError is HyperbrowserError
    for symbol in (
        "docker_build_context_fingerprint",
        "DockerBuildContextChangedError",
        "image_build_name",
        "docker_image_digest",
        "DockerCommandError",
    ):
        assert hasattr(hyperbrowser, symbol), symbol
        assert symbol in hyperbrowser.__all__, symbol
        assert hasattr(image_builds, symbol), symbol
        assert symbol in image_builds.__all__, symbol
        assert getattr(hyperbrowser, symbol) is getattr(image_builds, symbol)

    assert issubclass(DockerCommandError, RuntimeError)

    assert "WebBotAuthParams" in session_types.__all__
    assert "ProxyRoute" in session_types.__all__

    for tool_symbol in (
        "FILL_CREDENTIAL_TOOL_OPENAI",
        "FILL_CREDENTIAL_TOOL_ANTHROPIC",
        "FILL_CREDENTIAL_TOOL_GEMINI",
        "FILL_CREDENTIAL_DESCRIPTION",
        "FILL_CREDENTIAL_SCHEMA",
    ):
        assert hasattr(tools, tool_symbol), tool_symbol
        assert tool_symbol in tools.__all__, tool_symbol

    assert models.GetActiveSessionsCountResponse is GetActiveSessionsCountResponse
    assert "GetActiveSessionsCountResponse" in models.__all__


def test_docker_command_error_raised_on_missing_or_failing_command(monkeypatch):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError("No such file or directory: 'docker'")

    monkeypatch.setattr("subprocess.run", raise_missing)
    with pytest.raises(DockerCommandError, match="docker CLI is required"):
        _run_command_result(["docker", "info"])


def test_transport_put_and_delete_accept_timeout_and_normalize_errors():
    for method_name in ("put", "delete"):
        sig = inspect.signature(getattr(TransportStrategy, method_name))
        assert "timeout" in sig.parameters
        assert sig.parameters["timeout"].default is None

    recorded_Timeouts = []

    class DummySyncClient:
        def put(self, url, json=None, timeout=None):
            recorded_Timeouts.append(("PUT", url, timeout))
            raise httpx.ReadTimeout("", request=httpx.Request("PUT", url))

        def delete(self, url, timeout=None):
            recorded_Timeouts.append(("DELETE", url, timeout))
            raise httpx.ConnectError(
                "connection reset", request=httpx.Request("DELETE", url)
            )

    sync_transport = SyncTransport.__new__(SyncTransport)
    sync_transport.client = DummySyncClient()

    with pytest.raises(HyperbrowserError) as put_exc:
        sync_transport.put(
            "https://api.hyperbrowser.ai/api/session/s1/stop", timeout=12.5
        )
    assert put_exc.value.retryable is True
    assert put_exc.value.service == "control"
    assert "[PUT /api/session/s1/stop]" in str(put_exc.value)

    with pytest.raises(HyperbrowserError) as del_exc:
        sync_transport.delete("https://api.hyperbrowser.ai/api/volume/v1", timeout=7.0)
    assert del_exc.value.retryable is True
    assert del_exc.value.service == "control"
    assert "[DELETE /api/volume/v1]" in str(del_exc.value)
    assert recorded_Timeouts == [
        ("PUT", "https://api.hyperbrowser.ai/api/session/s1/stop", 12.5),
        ("DELETE", "https://api.hyperbrowser.ai/api/volume/v1", 7.0),
    ]


@pytest.mark.anyio
async def test_async_transport_put_and_delete_accept_timeout_and_normalize_errors():
    recorded_timeouts = []

    class DummyAsyncClient:
        async def put(self, url, json=None, timeout=None):
            recorded_timeouts.append(("PUT", url, timeout))
            raise httpx.ReadTimeout("", request=httpx.Request("PUT", url))

        async def delete(self, url, timeout=None):
            recorded_timeouts.append(("DELETE", url, timeout))
            raise httpx.ConnectError(
                "connection reset", request=httpx.Request("DELETE", url)
            )

    async_transport = AsyncTransport.__new__(AsyncTransport)
    async_transport._closed = True
    async_transport.client = DummyAsyncClient()

    with pytest.raises(HyperbrowserError) as put_exc:
        await async_transport.put(
            "https://api.hyperbrowser.ai/api/session/s1/stop", timeout=15.0
        )
    assert put_exc.value.retryable is True
    assert put_exc.value.service == "control"
    assert "[PUT /api/session/s1/stop]" in str(put_exc.value)

    with pytest.raises(HyperbrowserError) as del_exc:
        await async_transport.delete(
            "https://api.hyperbrowser.ai/api/volume/v1", timeout=9.0
        )
    assert del_exc.value.retryable is True
    assert del_exc.value.service == "control"
    assert "[DELETE /api/volume/v1]" in str(del_exc.value)
    assert recorded_timeouts == [
        ("PUT", "https://api.hyperbrowser.ai/api/session/s1/stop", 15.0),
        ("DELETE", "https://api.hyperbrowser.ai/api/volume/v1", 9.0),
    ]


@pytest.mark.anyio
async def test_handle_response_normalizes_request_error_with_metadata():
    request = httpx.Request("POST", "https://api.hyperbrowser.ai/api/session")

    class BrokenResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def __init__(self):
            self.request = request

        def raise_for_status(self):
            return None

        @property
        def content(self):
            raise httpx.ReadError("stream interrupted", request=request)

    sync_transport = SyncTransport.__new__(SyncTransport)
    with pytest.raises(HyperbrowserError) as sync_exc:
        sync_transport._handle_response(BrokenResponse())
    assert sync_exc.value.retryable is True
    assert sync_exc.value.service == "control"
    assert isinstance(sync_exc.value.cause, httpx.ReadError)
    assert "[POST /api/session]" in str(sync_exc.value)

    async_transport = AsyncTransport.__new__(AsyncTransport)
    async_transport._closed = True
    with pytest.raises(HyperbrowserError) as async_exc:
        await async_transport._handle_response(BrokenResponse())
    assert async_exc.value.retryable is True
    assert async_exc.value.service == "control"
    assert isinstance(async_exc.value.cause, httpx.ReadError)
    assert "[POST /api/session]" in str(async_exc.value)


@pytest.mark.anyio
async def test_sandbox_hydrate_preserves_startup_secrets_and_removes_dead_helper():
    assert not hasattr(SandboxHandle, "_apply_runtime_session")
    assert not hasattr(AsyncSandboxHandle, "_apply_runtime_session")

    initial_payload = {
        **SANDBOX_DETAIL_PAYLOAD,
        "startupSecrets": [
            {
                "env": "API_TOKEN",
                "id": "sec_1",
                "name": "my-secret",
                "version": 2,
            }
        ],
    }
    refreshed_payload = {
        **SANDBOX_DETAIL_PAYLOAD,
        "status": "active",
    }

    sync_service = SimpleNamespace(
        runtime_timeout=30,
        runtime_proxy_override=None,
        get_detail=lambda sandbox_id: SandboxDetail(**refreshed_payload),
    )
    handle = SandboxHandle(sync_service, SandboxDetail(**initial_payload))
    assert handle.startup_secrets is not None
    assert len(handle.startup_secrets) == 1
    assert handle.startup_secrets[0].env == "API_TOKEN"

    info = handle.info()
    assert info.startup_secrets is not None
    assert info.startup_secrets[0].env == "API_TOKEN"
    assert handle.startup_secrets is not None
    assert handle.startup_secrets[0].env == "API_TOKEN"
    assert handle.to_dict()["startup_secrets"][0]["env"] == "API_TOKEN"

    async def async_get_detail(sandbox_id):
        return SandboxDetail(**refreshed_payload)

    async_service = SimpleNamespace(
        runtime_timeout=30,
        runtime_proxy_override=None,
        get_detail=async_get_detail,
    )
    async_handle = AsyncSandboxHandle(async_service, SandboxDetail(**initial_payload))
    async_info = await async_handle.info()
    assert async_info.startup_secrets is not None
    assert async_info.startup_secrets[0].env == "API_TOKEN"
    assert async_handle.startup_secrets is not None
    assert async_handle.startup_secrets[0].env == "API_TOKEN"


@pytest.mark.anyio
async def test_sandbox_manager_url_encodes_path_parameters():
    build_payload = {
        "build": {
            "id": "build/1",
            "imageName": "img",
            "namespace": "team_1",
            "status": "completed",
            "createdAt": "2026-03-12T00:00:00Z",
            "updatedAt": "2026-03-12T00:00:01Z",
        }
    }

    def make_handler(paths):
        def handler(request: httpx.Request):
            paths.append((request.method, request.url.raw_path.decode("ascii")))
            path = request.url.path
            if path.startswith("/api/images/builds/"):
                return httpx.Response(200, json=build_payload)
            if path.startswith("/api/images/"):
                return httpx.Response(
                    200,
                    json={"id": "img_1", "imageName": "org/name:tag", "deleted": True},
                )
            if path.startswith("/api/snapshots/"):
                if request.method == "DELETE":
                    return httpx.Response(
                        200,
                        json={
                            "id": "snap_1",
                            "snapshotName": "snap/name#1",
                            "deleted": True,
                        },
                    )
                return httpx.Response(
                    200, json={"snapshot": SNAPSHOT_LIST_PAYLOAD["snapshots"][0]}
                )
            if path.endswith("/stop"):
                return httpx.Response(200, json={"success": True})
            if path.endswith("/snapshot"):
                return httpx.Response(200, json=SNAPSHOT_RESULT_PAYLOAD)
            if path.endswith("/network"):
                return httpx.Response(
                    200,
                    json={
                        "sandboxId": "sbx/1",
                        "network": {
                            "allowInternetAccess": True,
                            "allowOut": [],
                            "denyOut": [],
                        },
                    },
                )
            if path.endswith("/expose"):
                return httpx.Response(
                    200,
                    json={
                        "port": 3000,
                        "auth": False,
                        "url": "https://3000-sbx.runtime.example.com/",
                    },
                )
            if path.endswith("/unexpose"):
                return httpx.Response(200, json={"port": 3000, "exposed": False})
            if path.endswith("/processes"):
                return httpx.Response(200, json={"process": {"id": "proc_1"}})
            return httpx.Response(200, json=SANDBOX_DETAIL_PAYLOAD)

        return handler

    sync_paths = []
    client = Hyperbrowser.__new__(Hyperbrowser)
    client.config = SimpleNamespace(
        api_key="test",
        base_url="https://api.hyperbrowser.ai",
        runtime_proxy_override=None,
    )
    client.timeout = 30
    client.transport = SyncTransport.__new__(SyncTransport)
    client.transport.client = httpx.Client(
        transport=httpx.MockTransport(make_handler(sync_paths))
    )
    from hyperbrowser.client.managers.sync_manager.sandbox import SandboxManager

    mgr = SandboxManager(client)
    mgr.delete_image("org/image:tag")
    mgr.get_snapshot("snap/1?x=2")
    mgr.delete_snapshot("snap/1?x=2")
    mgr.stop("sbx/1#a")
    mgr.get_image_build("bld/1?y=2")
    mgr.complete_image_build(
        "bld/1?y=2",
        {
            "input_sha256": "a" * 64,
            "input_size_bytes": 10,
            "input_format": "docker_image_manifest_v1",
        },
    )
    mgr.cancel_image_build("bld/1?y=2")
    mgr.get_detail("sbx/1#a")
    mgr.create_memory_snapshot("sbx/1#a")
    mgr.update_network("sbx/1#a", {"allow_internet_access": True})
    mgr.expose("sbx/1#a", {"port": 3000})
    mgr.unexpose("sbx/1#a", 3000)
    mgr.start_secret_process("sbx/1#a", {"command": "echo"})
    client.transport.close()

    expected = [
        ("DELETE", "/api/images/org%2Fimage%3Atag"),
        ("GET", "/api/snapshots/snap%2F1%3Fx%3D2"),
        ("DELETE", "/api/snapshots/snap%2F1%3Fx%3D2"),
        ("PUT", "/api/sandbox/sbx%2F1%23a/stop"),
        ("GET", "/api/images/builds/bld%2F1%3Fy%3D2"),
        ("POST", "/api/images/builds/bld%2F1%3Fy%3D2/complete"),
        ("POST", "/api/images/builds/bld%2F1%3Fy%3D2/cancel"),
        ("GET", "/api/sandbox/sbx%2F1%23a"),
        ("POST", "/api/sandbox/sbx%2F1%23a/snapshot"),
        ("PUT", "/api/sandbox/sbx%2F1%23a/network"),
        ("POST", "/api/sandbox/sbx%2F1%23a/expose"),
        ("GET", "/api/sandbox/sbx%2F1%23a"),
        ("POST", "/api/sandbox/sbx%2F1%23a/unexpose"),
        ("POST", "/api/sandbox/sbx%2F1%23a/processes"),
    ]
    assert sync_paths == expected

    async_paths = []
    async_client = AsyncHyperbrowser.__new__(AsyncHyperbrowser)
    async_client.config = SimpleNamespace(
        api_key="test",
        base_url="https://api.hyperbrowser.ai",
        runtime_proxy_override=None,
    )
    async_client.timeout = 30
    async_client.transport = AsyncTransport.__new__(AsyncTransport)
    async_client.transport._closed = False
    async_client.transport.client = httpx.AsyncClient(
        transport=httpx.MockTransport(make_handler(async_paths))
    )
    from hyperbrowser.client.managers.async_manager.sandbox import (
        SandboxManager as AsyncSandboxManager,
    )

    async_mgr = AsyncSandboxManager(async_client)
    await async_mgr.delete_image("org/image:tag")
    await async_mgr.get_snapshot("snap/1?x=2")
    await async_mgr.delete_snapshot("snap/1?x=2")
    await async_mgr.stop("sbx/1#a")
    await async_mgr.get_image_build("bld/1?y=2")
    await async_mgr.complete_image_build(
        "bld/1?y=2",
        {
            "input_sha256": "a" * 64,
            "input_size_bytes": 10,
            "input_format": "docker_image_manifest_v1",
        },
    )
    await async_mgr.cancel_image_build("bld/1?y=2")
    await async_mgr.get_detail("sbx/1#a")
    await async_mgr.create_memory_snapshot("sbx/1#a")
    await async_mgr.update_network("sbx/1#a", {"allow_internet_access": True})
    await async_mgr.expose("sbx/1#a", {"port": 3000})
    await async_mgr.unexpose("sbx/1#a", 3000)
    await async_mgr.start_secret_process("sbx/1#a", {"command": "echo"})
    await async_client.transport.close()

    assert async_paths == expected


@pytest.mark.anyio
async def test_session_webgl_fingerprinting_solver_type_and_active_count():
    params = CreateSessionParams(enable_webgl_fingerprinting=True)
    dumped = params.model_dump(by_alias=True, exclude_none=True)
    assert dumped["enableWebglFingerprinting"] is True

    launch_state = SessionLaunchState(
        solverType="future-solver-v2", enableWebglFingerprinting=True
    )
    assert launch_state.solver_type == "future-solver-v2"
    assert launch_state.enable_webgl_fingerprinting is True

    def handler(request: httpx.Request):
        assert request.method == "GET"
        assert request.url.path == "/api/sessions/active-count"
        return httpx.Response(
            200,
            json={
                "activeSessionsCount": 3,
                "maxConcurrentSessions": 10,
                "totalActiveSessionsCount": 4,
            },
        )

    client = Hyperbrowser.__new__(Hyperbrowser)
    client.config = SimpleNamespace(
        api_key="test", base_url="https://api.hyperbrowser.ai"
    )
    client.timeout = 30
    client.transport = SyncTransport.__new__(SyncTransport)
    client.transport.client = httpx.Client(transport=httpx.MockTransport(handler))
    from hyperbrowser.client.managers.sync_manager.session import SessionManager

    session_mgr = SessionManager(client)
    res = session_mgr.get_active_sessions_count()
    assert res.active_sessions_count == 3
    assert res.max_concurrent_sessions == 10
    assert res.total_active_sessions_count == 4
    client.transport.close()

    async_client = AsyncHyperbrowser.__new__(AsyncHyperbrowser)
    async_client.config = SimpleNamespace(
        api_key="test", base_url="https://api.hyperbrowser.ai"
    )
    async_client.timeout = 30
    async_client.transport = AsyncTransport.__new__(AsyncTransport)
    async_client.transport._closed = False
    async_client.transport.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )
    from hyperbrowser.client.managers.async_manager.session import (
        SessionManager as AsyncSessionManager,
    )

    async_session_mgr = AsyncSessionManager(async_client)
    async_res = await async_session_mgr.get_active_sessions_count()
    assert async_res.active_sessions_count == 3
    assert async_res.max_concurrent_sessions == 10
    assert async_res.total_active_sessions_count == 4
    await async_client.transport.close()


@pytest.mark.anyio
async def test_browser_use_tool_falls_back_to_error_and_credential_fill_validates_session_id():
    failed_response = BrowserUseTaskResponse(
        jobId="job_1",
        status="failed",
        data=BrowserUseTaskData(steps=[], finalResult=None),
        error="Task timed out",
    )
    sync_hb = SimpleNamespace(
        agents=SimpleNamespace(
            browser_use=SimpleNamespace(start_and_wait=lambda params: failed_response)
        )
    )
    assert tools.BrowserUseTool.runnable(sync_hb, {"task": "do something"}) == (
        "Task timed out"
    )

    async def async_start_and_wait(params):
        return failed_response

    async_hb = SimpleNamespace(
        agents=SimpleNamespace(
            browser_use=SimpleNamespace(start_and_wait=async_start_and_wait)
        )
    )
    assert (
        await tools.BrowserUseTool.async_runnable(async_hb, {"task": "do something"})
        == "Task timed out"
    )

    from hyperbrowser.client.managers.async_manager.session_credentials import (
        SessionCredentialsManager as AsyncSessionCredentialsManager,
    )
    from hyperbrowser.client.managers.sync_manager.session_credentials import (
        SessionCredentialsManager,
    )

    sync_creds = SessionCredentialsManager(SimpleNamespace())
    for invalid_id in ("", "   ", None):
        with pytest.raises(HyperbrowserError, match="A session ID is required") as exc:
            sync_creds.fill(
                invalid_id,
                {"credential": "my-secret", "fields": [{"selector": "#pw"}]},
            )
        assert exc.value.code == "invalid_request"

    async_creds = AsyncSessionCredentialsManager(SimpleNamespace())
    for invalid_id in ("", "   ", None):
        with pytest.raises(HyperbrowserError, match="A session ID is required") as exc:
            await async_creds.fill(
                invalid_id,
                {"credential": "my-secret", "fields": [{"selector": "#pw"}]},
            )
        assert exc.value.code == "invalid_request"
