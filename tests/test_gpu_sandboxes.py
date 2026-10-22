"""GPU contracts shared with node-sdk, exercised through sync and async HTTP."""

import asyncio
import inspect
import json
from pathlib import Path
from threading import Event

import httpx
import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.client._request import dump_request
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.image_builds import image_build_name
from hyperbrowser.models import (
    CreateSandboxImageBuildParams,
    CreateSandboxParams,
    SandboxDetail,
    SandboxListParams,
    ScreenshotActionParams,
)

CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/gpu_contract.json").read_text()
)
PARAMS = dict(
    image_name="gpu-image",
    gpu="H100",
    gpu_count=2,
    preempt=False,
    region="us",
    cpu=8,
    memory_mib=32768,
    disk_mib=524288,
    enable_recording=True,
    exposed_ports=[{"port": 8000, "auth": True}],
    allow_internet_access=True,
    allow_out=["example.com"],
    deny_out=[],
)


async def call(result):
    return await result if inspect.isawaitable(result) else result


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def run_sdk(request, monkeypatch):
    sync_http, async_http = httpx.Client, httpx.AsyncClient

    def run(handler, scenario):
        transport = httpx.MockTransport(handler)

        async def invoke():
            cls = AsyncHyperbrowser if request.param else Hyperbrowser
            client = cls(api_key="control-key", base_url="https://control.test")
            try:
                await scenario(client.sandboxes)
            finally:
                await call(client.close())

        with monkeypatch.context() as patch:
            patch.setattr(
                httpx, "Client", lambda **kw: sync_http(transport=transport, **kw)
            )
            patch.setattr(
                httpx, "AsyncClient", lambda **kw: async_http(transport=transport, **kw)
            )
            asyncio.run(invoke())

    return run


@pytest.mark.parametrize("legacy", [False, True])
def test_gpu_launch_serialization_and_provisioning(run_sdk, legacy):
    def handler(request):
        assert request.method == "POST" and request.url.path == "/api/sandbox"
        assert json.loads(request.content) == CONTRACT["create"]
        return httpx.Response(200, json=CONTRACT["provisioning"])

    async def scenario(service):
        sandbox = await call(
            service.create(CreateSandboxParams(**PARAMS) if legacy else PARAMS)
        )
        assert sandbox.status == "provisioning" and sandbox.runtime is None
        assert sandbox.gpu_type == "H100" and sandbox.gpu_count == 2
        assert sandbox.preempt is False and sandbox.recording_enabled is True
        assert sandbox.capabilities.writable_storage == "disk"
        assert sandbox.capabilities.live_network_updates is True
        with pytest.raises(HyperbrowserError, match="wait_until_ready"):
            await call(sandbox.exec("nvidia-smi"))
        with pytest.raises(HyperbrowserError, match="not ready"):
            sandbox.get_exposed_url(8000)

    run_sdk(handler, scenario)


@pytest.mark.parametrize(
    "overrides",
    [
        {"gpu": None},
        {"gpu_count": 0},
        {"gpu_count": 9},
        {"gpu_count": 1.5},
        {"gpu_count": True},
        {"preempt": "false"},
        {"gpu": "A100"},
        {"runtime_class": "firecracker"},
        {"region": "us-east"},
        {"disk_mib": 12287},
        {"disk_mib": 524289},
        {"image_name": None, "snapshot_name": "snapshot"},
        {"mounts": {"/data": {"id": "volume"}}},
        {"secrets": {"TOKEN": "token"}},
    ],
)
def test_invalid_gpu_requests_are_rejected(overrides):
    with pytest.raises(ValueError):
        CreateSandboxParams(**dict(PARAMS, **overrides))


def test_defaults_stay_server_owned_and_list_filter_remains_compatible():
    assert dump_request({"image_name": "gpu", "gpu": "B300"}, CreateSandboxParams) == {
        "imageName": "gpu",
        "gpu": "B300",
    }
    with pytest.raises(ValueError):
        SandboxListParams(status="provisioning")


def test_wait_retries_reads_and_hydrates_runtime(run_sdk):
    requests = []

    def handler(request):
        requests.append((request.method, request.url.path))
        assert request.method == "GET"
        if len(requests) == 1:
            return httpx.Response(503, json={"message": "temporarily unavailable"})
        return httpx.Response(200, json=CONTRACT["active"])

    async def scenario(service):
        sandbox = service.attach(SandboxDetail(**CONTRACT["provisioning"]))
        assert await call(sandbox.wait_until_ready(poll_interval=0)) is sandbox
        assert sandbox.status == "active" and sandbox.runtime.base_url.endswith(
            sandbox.id
        )
        assert (await call(sandbox.create_runtime_session())).token == "runtime-token"

    run_sdk(handler, scenario)
    assert requests == [("GET", "/api/sandbox/gpu-sandbox-1")] * 2


@pytest.mark.parametrize(
    "failure", ["closed", "timeout", "cancelled", "forbidden", "wrong_id"]
)
def test_wait_failures_never_stop_or_recreate(run_sdk, failure):
    requests = []

    def handler(request):
        requests.append(request.method)
        assert request.method == "GET"
        if failure == "forbidden":
            return httpx.Response(403, json={"message": "forbidden"})
        if failure == "wrong_id":
            return httpx.Response(200, json=dict(CONTRACT["active"], id="other"))
        return httpx.Response(200, json=CONTRACT["closed"])

    async def scenario(service):
        sandbox = service.attach(SandboxDetail(**CONTRACT["provisioning"]))
        event = Event()
        if failure == "cancelled":
            event.set()
        with pytest.raises(HyperbrowserError) as caught:
            await call(
                sandbox.wait_until_ready(
                    timeout=0 if failure == "timeout" else 1,
                    poll_interval=0,
                    cancel_event=event,
                )
            )
        expected = {
            "closed": "sandbox_not_running",
            "timeout": "wait_timeout",
            "cancelled": "wait_cancelled",
        }
        if failure in expected:
            assert caught.value.code == expected[failure]
            assert caught.value.details["sandboxId"] == sandbox.id
        if failure == "closed":
            assert sandbox.close_reason == "preempted"
            assert sandbox.info  # The handle remains usable for inspection.
            assert sandbox.to_dict()["credits_used"] == 1.25
        if failure == "forbidden":
            assert caught.value.status_code == 403
        if failure == "wrong_id":
            assert "different ID" in str(caught.value)

    run_sdk(handler, scenario)
    assert requests == ([] if failure in ("timeout", "cancelled") else ["GET"])


def test_runtime_actions_refresh_token_and_keep_browser_auth_separate(run_sdk):
    actions = []

    def handler(request):
        if request.url.host == "control.test":
            return httpx.Response(
                200, json=dict(CONTRACT["active"], token="fresh-token")
            )
        assert request.url.path == "/sandbox/gpu-sandbox-1/computer-action"
        assert request.method == "POST"
        actions.append(
            (request.headers.get("authorization"), json.loads(request.content))
        )
        if len(actions) == 1:
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(200, json={"success": True, "screenshot": "cG5n"})

    async def scenario(service):
        sandbox = service.attach(SandboxDetail(**CONTRACT["active"]))
        result = await call(sandbox.computer_action(ScreenshotActionParams()))
        assert result.screenshot == "cG5n"
        await call(
            sandbox.computer_action(
                {"action": "click", "x": 4, "y": 5, "num_clicks": 2}
            )
        )

    run_sdk(handler, scenario)
    assert actions[0] == ("Bearer runtime-token", {"action": "screenshot"})
    assert actions[1] == ("Bearer fresh-token", {"action": "screenshot"})
    assert actions[2][1]["numClicks"] == 2


def test_gpu_network_and_authenticated_ports(run_sdk):
    def handler(request):
        body = json.loads(request.content)
        if request.url.path.endswith("/network"):
            assert body == {"allowOut": ["example.com"], "denyOut": []}
            return httpx.Response(
                200, json={"network": {"allowInternetAccess": True, **body}}
            )
        assert request.url.path.endswith("/expose") and body == {
            "port": 8000,
            "auth": True,
        }
        return httpx.Response(
            200,
            json={
                "port": 8000,
                "auth": True,
                "url": "https://8000.runtime.test/",
                "browserUrl": "https://8000.runtime.test/auth",
            },
        )

    async def scenario(service):
        sandbox = service.attach(SandboxDetail(**CONTRACT["active"]))
        await call(
            sandbox.update_network({"allow_out": ["example.com"], "deny_out": []})
        )
        assert sandbox.network.allow_out == ["example.com"]
        exposure = await call(sandbox.expose({"port": 8000, "auth": True}))
        assert exposure.auth and exposure.browser_url.endswith("/auth")

    run_sdk(handler, scenario)


def test_gpu_image_publication_wait(run_sdk):
    polls = []

    def handler(request):
        polls.append(request.url.path)
        return httpx.Response(
            200, json={"build": CONTRACT["building" if len(polls) == 1 else "gpuReady"]}
        )

    async def scenario(service):
        build = await call(service.wait_for_image_build("gpu-build-1", poll_interval=0))
        assert build.gpu_image_ready and build.gpu_uploaded

    run_sdk(handler, scenario)
    assert len(polls) == 2


def test_gpu_image_publication_failure(run_sdk):
    def handler(request):
        build = dict(
            CONTRACT["building"], metadata={"ociPublicationError": "internal-error"}
        )
        return httpx.Response(200, json={"build": build})

    async def scenario(service):
        with pytest.raises(RuntimeError, match="GPU image publication failed"):
            await call(service.wait_for_image_build("gpu-build-1", poll_interval=0))

    run_sdk(handler, scenario)


def test_gpu_image_identity_and_unsupported_input():
    cpu = image_build_name(source="dockerfile", fingerprint="a" * 64)
    gpu = image_build_name(
        source="dockerfile", fingerprint="a" * 64, enable_gpu_builds=True
    )
    assert cpu != gpu
    assert cpu == image_build_name(
        source="dockerfile", fingerprint="a" * 64, enable_gpu_builds=False
    )
    with pytest.raises(ValueError, match="remote Dockerfile"):
        CreateSandboxImageBuildParams(
            image_name="gpu",
            input_sha256="a" * 64,
            input_size_bytes=1,
            enable_gpu_builds=True,
            input_format="docker_image_manifest_v1",
        )


@pytest.mark.parametrize(
    "mode", ["created", "joined", "reused", "cpu_only", "detached"]
)
def test_gpu_build_resolution(run_sdk, tmp_path, mode):
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    name = image_build_name(
        source="dockerfile", fingerprint="a" * 64, enable_gpu_builds=True
    )
    calls = []
    polls = []

    def build(ready=False):
        return dict(CONTRACT["gpuReady" if ready else "building"], imageName=name)

    def handler(request):
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path == "/api/images/builds" and request.method == "GET":
            rows = (
                [build(ready=mode == "reused")]
                if mode in ("reused", "cpu_only")
                else []
            )
            if mode == "cpu_only":
                rows[0]["enableGPUBuilds"] = False
            return httpx.Response(200, json={"builds": rows})
        if path == "/api/images":
            return httpx.Response(
                200,
                json={
                    "images": [
                        dict(
                            id="gpu-image-1",
                            imageName=name,
                            namespace="team-1",
                            uploaded=True,
                            createdAt="2026-10-22T00:00:00Z",
                            updatedAt="2026-10-22T00:00:00Z",
                        )
                    ]
                },
            )
        if path == "/api/images/builds":
            assert json.loads(request.content)["enableGPUBuilds"] is True
            if mode == "joined":
                return httpx.Response(
                    409,
                    json={
                        "message": "in progress",
                        "code": "image_build_in_progress",
                        "build": build(),
                    },
                )
            return httpx.Response(200, json={"build": build(), "uploads": []})
        if path.endswith("/complete"):
            return httpx.Response(200, json={"build": build()})
        assert path == "/api/images/builds/gpu-build-1" and request.method == "GET"
        polls.append(path)
        return httpx.Response(200, json={"build": build(ready=len(polls) > 1)})

    async def scenario(service):
        # Fingerprint must describe the actual context before upload.
        from hyperbrowser.build_context import docker_build_context_fingerprint

        nonlocal name
        fingerprint = docker_build_context_fingerprint(tmp_path)
        name = image_build_name(
            source="dockerfile", fingerprint=fingerprint, enable_gpu_builds=True
        )
        result = await call(
            service.get_or_build_image(
                context_path=tmp_path,
                enable_gpu_builds=True,
                poll_interval=0,
                wait=mode != "detached",
            )
        )
        assert result.outcome == {"joined": "joined", "reused": "reused"}.get(
            mode, "created"
        )
        assert result.image_id == (None if mode == "detached" else "gpu-image-1")

    run_sdk(handler, scenario)
    assert not any(path.endswith("/cancel") for _, path in calls)
    assert len(polls) == (0 if mode in ("reused", "detached") else 2)


@pytest.mark.parametrize("reason", ["timeout", "cancel"])
def test_async_wait_interrupts_pending_read(reason):
    from types import SimpleNamespace
    from hyperbrowser.client.managers.async_manager.sandbox import SandboxHandle

    async def scenario():
        entered = asyncio.Event()

        async def get_detail(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        service = SimpleNamespace(
            get_detail=get_detail, runtime_timeout=30, runtime_proxy_override=None
        )
        sandbox = SandboxHandle(service, SandboxDetail(**CONTRACT["provisioning"]))
        task = asyncio.create_task(
            sandbox.wait_until_ready(timeout=0.01 if reason == "timeout" else None)
        )
        await entered.wait()
        if reason == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(HyperbrowserError) as caught:
                await task
            assert caught.value.code == "wait_timeout"
        assert sandbox.status == "provisioning"

    asyncio.run(scenario())


def test_gpu_image_wait_timeout_leaves_build_running(run_sdk):
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json={"build": CONTRACT["building"]})

    async def scenario(service):
        with pytest.raises(TimeoutError):
            await call(service.wait_for_image_build("gpu-build-1", timeout=0))

    run_sdk(handler, scenario)
    assert calls == ["GET"]


def test_gpu_prebuilt_helpers_reject_before_packaging(run_sdk):
    def handler(request):
        pytest.fail("Unsupported GPU build must fail before a request")

    async def scenario(service):
        with pytest.raises(ValueError, match="remote Dockerfile"):
            await call(
                service.build_image_from_docker_image(
                    docker_image="cuda", image_name="gpu", enable_gpu_builds=True
                )
            )
        with pytest.raises(ValueError, match="remote=True"):
            await call(
                service.build_image_from_dockerfile(
                    context_path="/missing",
                    image_name="gpu",
                    remote=False,
                    enable_gpu_builds=True,
                )
            )

    run_sdk(handler, scenario)
