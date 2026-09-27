import asyncio
import inspect
import json

import httpx
import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.build_context import DockerBuildContextChangedError
from hyperbrowser.client.managers.sandboxes import image_build
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.image_builds import image_build_name
from hyperbrowser.models import SandboxImageInit


class Backend:
    def __init__(self, *, ready=False, conflict=False):
        self.ready = ready
        self.conflict = conflict
        self.name = None
        self.requests = []
        self.upload_timeouts = []
        self.polls = 0
        self.transform = lambda value: value

    def build(self, status="building"):
        return {
            "id": "build-1",
            "imageName": self.name,
            "imageId": "image-1",
            "status": status,
            "metadata": {
                "inputFormat": "dockerfile_context_manifest_v1",
                "sourcePlatform": "linux/amd64",
            },
        }

    def respond(self, request):
        path = request.url.path
        self.requests.append((request.method, path))
        if path == "/api/images":
            self.name = request.url.params["search"]
            image = {
                "id": "image-1",
                "imageName": self.name,
                "namespace": "team-local",
                "uploaded": False,
                "ready": True,
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
            }
            return httpx.Response(200, json={"images": [image] if self.ready else []})
        if request.method == "POST" and path == "/api/images/builds":
            body = json.loads(request.content)
            self.name = body["imageName"]
            if self.conflict:
                return httpx.Response(
                    409,
                    json=self.transform(
                        {
                            "message": "already building",
                            "code": "image_build_in_progress",
                            "build": self.build(),
                        }
                    ),
                )
            return httpx.Response(
                200, json={"build": self.build("awaiting_upload"), "uploads": []}
            )
        if path.endswith("/complete"):
            return httpx.Response(200, json={"build": self.build()})
        if path.endswith("/reuse"):
            self.name = json.loads(request.content)["imageName"]
            return httpx.Response(
                200, json={"hit": True, "build": self.build("completed")}
            )
        assert request.method == "GET" and path == "/api/images/builds/build-1", path
        self.polls += 1
        return httpx.Response(200, json={"build": self.build("completed")})


@pytest.fixture
def context(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY data /data\n")
    (tmp_path / "data").write_text("first")
    return tmp_path


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def resolve(request, monkeypatch):
    """Use real SDK request, packaging, resolution and polling implementations."""
    asynchronous = request.param
    sync_http, async_http = httpx.Client, httpx.AsyncClient

    def run(backend, **kwargs):
        async def invoke():
            factory = AsyncHyperbrowser if asynchronous else Hyperbrowser
            client = factory(api_key="local-only", base_url="http://local.test")
            try:
                result = client.sandboxes.get_or_build_image(poll_interval=0, **kwargs)
                return await result if inspect.isawaitable(result) else result
            finally:
                result = client.close()
                if inspect.isawaitable(result):
                    await result

        transport = httpx.MockTransport(backend.respond)
        with monkeypatch.context() as patch:
            patch.setattr(
                httpx, "Client", lambda **kw: sync_http(transport=transport, **kw)
            )
            patch.setattr(
                httpx, "AsyncClient", lambda **kw: async_http(transport=transport, **kw)
            )
            return asyncio.run(invoke())

    return run


@pytest.mark.parametrize("mode", ["ready", "created", "joined", "forced", "detached"])
def test_resolves_ready_new_and_concurrent_builds(context, resolve, mode):
    backend = Backend(ready=mode in ("ready", "forced"), conflict=mode == "joined")
    result = resolve(
        backend,
        context_path=context,
        force_build=mode == "forced",
        wait=mode != "detached",
    )
    assert result.outcome == {"ready": "reused", "joined": "joined"}.get(
        mode, "created"
    )
    assert result.image_name.startswith("hb__dockerfile__")
    assert result.image_id == (None if mode == "detached" else "image-1")
    assert backend.polls == int(mode not in ("ready", "detached"))
    if mode == "ready":
        assert backend.requests == [("GET", "/api/images")]
    if mode == "forced":
        assert ("GET", "/api/images") not in backend.requests
    assert not any(path.endswith("/cancel") for _, path in backend.requests)


@pytest.mark.parametrize(
    "mismatch",
    ["name", "format", "platform", "missing-status", "missing-build", "code"],
)
def test_incompatible_conflicts_are_not_joined(context, resolve, mismatch):
    backend = Backend(conflict=True)

    def transform(payload):
        if mismatch == "name":
            payload["build"]["imageName"] = "unrelated"
        elif mismatch == "format":
            payload["build"]["metadata"]["inputFormat"] = "docker_image_manifest_v1"
        elif mismatch == "platform":
            payload["build"]["metadata"]["sourcePlatform"] = "linux/arm64"
        elif mismatch == "missing-status":
            del payload["build"]["status"]
        elif mismatch == "missing-build":
            del payload["build"]
        else:
            payload["code"] = "different_conflict"
        return payload

    backend.transform = transform
    with pytest.raises(HyperbrowserError) as error:
        resolve(backend, context_path=context)
    assert error.value.status_code == 409
    assert backend.polls == 0


def test_context_change_during_lookup_fails_before_submission(context, resolve):
    backend = Backend()
    respond = backend.respond

    def mutate(request):
        response = respond(request)
        if request.url.path == "/api/images":
            (context / "data").write_text("changed")
        return response

    backend.respond = mutate
    with pytest.raises(DockerBuildContextChangedError):
        resolve(backend, context_path=context)
    assert backend.requests == [("GET", "/api/images")]


@pytest.mark.parametrize(
    "uploaded,ready", [(True, None), (False, True), (False, False), (False, None)]
)
def test_ready_lookup_supports_old_servers_and_does_not_reuse_pending_rows(
    context, resolve, uploaded, ready
):
    backend = Backend(ready=True)
    original = backend.respond

    def respond(request):
        response = original(request)
        if request.url.path == "/api/images":
            payload = response.json()
            payload["images"][0]["uploaded"] = uploaded
            if ready is None:
                del payload["images"][0]["ready"]
            else:
                payload["images"][0]["ready"] = ready
            return httpx.Response(200, json=payload)
        return response

    backend.respond = respond
    result = resolve(backend, context_path=context)
    assert result.outcome == ("reused" if uploaded or ready else "created")


def test_exact_ready_lookup_searches_later_pages(context, resolve):
    backend = Backend(ready=True)
    original = backend.respond
    pages = []

    def respond(request):
        response = original(request)
        if request.url.path == "/api/images":
            page = int(request.url.params["page"])
            pages.append(page)
            payload = response.json()
            payload["totalCount"] = 101
            if page == 1:
                template = payload["images"][0]
                payload["images"] = [
                    dict(template, imageName="unrelated-" + str(i)) for i in range(100)
                ]
            return httpx.Response(200, json=payload)
        return response

    backend.respond = respond
    assert resolve(backend, context_path=context).outcome == "reused"
    assert pages == [1, 2]


@pytest.mark.parametrize("changed", [False, True])
def test_docker_identity_is_verified_before_import(resolve, monkeypatch, changed):
    digest = "sha256:" + "a" * 64
    current = {"Id": digest, "Config": {}}
    monkeypatch.setattr(
        image_build, "_inspect_docker_image", lambda *args: dict(current)
    )
    backend = Backend()
    respond = backend.respond

    def lookup(request):
        response = respond(request)
        if changed and request.url.path == "/api/images":
            current["Id"] = "sha256:" + "b" * 64
        return response

    backend.respond = lookup
    if changed:
        with pytest.raises(RuntimeError, match="Docker image changed"):
            resolve(backend, docker_image="local/app:latest")
        assert backend.requests == [("GET", "/api/images")]
    else:
        result = resolve(backend, docker_image="local/app:latest")
        assert result.image_name == image_build_name(
            source="prebuilt", fingerprint=digest
        )
        assert result.image_id == "image-1"


@pytest.mark.parametrize(
    "message,unsupported",
    [
        (
            '"--platform" requires API version 1.49, but the Docker daemon API version is 1.48',
            True,
        ),
        ("unknown flag: --platform", True),
        ("Error response from daemon: No such image: local/app:latest", False),
        ("Cannot connect to the Docker daemon", False),
    ],
)
def test_docker_identity_errors_fail_before_http(
    resolve, monkeypatch, message, unsupported
):
    original = RuntimeError(message)
    calls = []

    def command(args):
        calls.append(args)
        raise original

    monkeypatch.setattr(image_build, "_run_command_output", command)
    backend = Backend()
    with pytest.raises(RuntimeError) as error:
        resolve(backend, docker_image="local/app:latest")
    if unsupported:
        assert "API 1.49 or newer (Docker 28.1+)" in str(error.value)
        assert "DOCKER_API_VERSION" in str(error.value)
        assert error.value.__cause__ is original
    else:
        assert error.value is original
    assert backend.requests == []
    assert len(calls) == 1
    assert calls[0][:3] == ["docker", "image", "inspect"]


@pytest.mark.parametrize("source", ["dockerfile", "known-digest"])
def test_remote_build_and_known_digest_cache_hit_need_no_docker(
    context, resolve, monkeypatch, source
):
    def command(*args, **kwargs):
        pytest.fail("This path must not invoke Docker")

    monkeypatch.setattr(image_build, "_run_command_result", command)
    backend = Backend(ready=source == "known-digest")
    kwargs = (
        {"context_path": context}
        if source == "dockerfile"
        else {
            "docker_image": "local/app:latest",
            "expected_image_digest": "sha256:" + "a" * 64,
        }
    )
    result = resolve(backend, **kwargs)
    assert result.outcome == ("created" if source == "dockerfile" else "reused")


def test_identity_separates_content_and_initialization_but_normalizes_dict_order():
    common = dict(source="dockerfile", fingerprint="a" * 64)
    default = image_build_name(**common)
    variants = [
        {"fingerprint": "b" * 64},
        {"name_prefix": "custom"},
        {"image_init": {"command": "start"}},
        {"image_config_user": "1000"},
    ]
    assert all(
        image_build_name(**{**common, **variant}) != default for variant in variants
    )
    assert image_build_name(
        **common, image_init={"env": {"A": "1", "B": "2"}}
    ) == image_build_name(
        **common, image_init=SandboxImageInit(env={"B": "2", "A": "1"})
    )
    assert len(image_build_name(**common, name_prefix="x" * 21)) <= 64


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"context_path": ".", "docker_image": "image"},
        {"context_path": ".", "expected_image_digest": "sha256:" + "a" * 64},
        {"docker_image": "image", "expected_context_fingerprint": "a" * 64},
        {"docker_image": "image", "remote_full_context": True},
    ],
)
def test_invalid_source_options_fail_without_http(resolve, kwargs):
    backend = Backend()
    with pytest.raises(ValueError):
        resolve(backend, **kwargs)
    assert backend.requests == []


@pytest.mark.parametrize("leave", ["cancel-one", "timeout-one", "cancel-both"])
@pytest.mark.anyio
async def test_independent_async_waiters_never_cancel_accepted_backend_build(
    context, monkeypatch, leave
):
    backend = Backend()
    polls = asyncio.Queue()
    release = asyncio.Event()

    async def respond(request):
        if request.method == "GET" and request.url.path == "/api/images/builds/build-1":
            backend.requests.append((request.method, request.url.path))
            polls.put_nowait(None)
            # Let the SDK enforce the short caller's polling deadline.
            if leave == "timeout-one" and not release.is_set():
                await asyncio.sleep(0.01)
                return httpx.Response(200, json={"build": backend.build()})
            await release.wait()
            return httpx.Response(200, json={"build": backend.build("completed")})
        response = backend.respond(request)
        if request.method == "POST" and request.url.path == "/api/images/builds":
            backend.conflict = True
        return response

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(respond), **kw),
    )
    async with AsyncHyperbrowser(
        api_key="local-only", base_url="http://local.test"
    ) as client:
        callers = []
        try:
            callers.append(
                asyncio.create_task(
                    client.sandboxes.get_or_build_image(
                        context_path=context,
                        poll_interval=0,
                        wait_timeout=0 if leave == "timeout-one" else 5,
                    )
                )
            )
            await asyncio.wait_for(polls.get(), 2)
            callers.append(
                asyncio.create_task(
                    client.sandboxes.get_or_build_image(
                        context_path=context,
                        poll_interval=0,
                        wait_timeout=5,
                    )
                )
            )
            await asyncio.wait_for(polls.get(), 2)
            if leave == "timeout-one":
                with pytest.raises(TimeoutError):
                    await callers[0]
            else:
                callers[0].cancel()
                with pytest.raises(asyncio.CancelledError):
                    await callers[0]
            assert not callers[1].done()
            if leave == "cancel-both":
                callers[1].cancel()
                with pytest.raises(asyncio.CancelledError):
                    await callers[1]
            else:
                release.set()
                result = await asyncio.wait_for(callers[1], 2)
                assert result.outcome == "joined" and result.image_id == "image-1"
            assert not any(path.endswith("/cancel") for _, path in backend.requests)
            assert sum(path.endswith("/complete") for _, path in backend.requests) == 1
        finally:
            release.set()
            for task in callers:
                if not task.done():
                    task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, TimeoutError):
                    pass
