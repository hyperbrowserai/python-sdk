import hashlib
import io
import json
import os
import subprocess
import tarfile
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

import hyperbrowser.client.managers.async_manager.sandbox as async_sandbox_module
import hyperbrowser.client.managers.sync_manager.sandbox as sync_sandbox_module
from hyperbrowser.client.managers.sandboxes import image_build
from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxManager as AsyncSandboxManager,
)
from hyperbrowser.client.managers.sync_manager.sandbox import SandboxManager
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    SandboxImageBuild,
    SandboxImageBuildCreateResult,
    SandboxImageBuildUpload,
)


def _image_build(
    status: str,
    *,
    error_code: str = "",
    error_message: str = "",
) -> SandboxImageBuild:
    return SandboxImageBuild(
        id="build-123",
        imageName="custom",
        status=status,
        errorCode=error_code,
        errorMessage=error_message,
    )


def test_image_build_model_rejects_invalid_status_casing():
    with pytest.raises(ValidationError):
        _image_build(" Completed ")


def test_build_docker_image_from_dockerfile_targets_linux_amd64(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, check, stdout, stderr, text):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(image_build.subprocess, "run", fake_run)
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")

    image_build.build_docker_image_from_dockerfile(
        context_path=tmp_path,
        dockerfile="Dockerfile",
        tag="local/app:test",
        build_args={"FOO": "bar"},
    )

    assert calls == [
        [
            "docker",
            "buildx",
            "build",
            "--platform",
            "linux/amd64",
            "-t",
            "local/app:test",
            "-f",
            str(tmp_path / "Dockerfile"),
            "--load",
            "--build-arg",
            "FOO=bar",
            str(tmp_path),
        ]
    ]


def test_package_docker_image_rejects_non_amd64_local_image(monkeypatch):
    def fake_run(args, check, stdout, stderr, text):
        assert args[:4] == ["docker", "image", "inspect", "--format"]
        return subprocess.CompletedProcess(args, 0, stdout="linux/arm64\n", stderr="")

    monkeypatch.setattr(image_build.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="expected linux/amd64"):
        image_build.package_docker_image("local/app:latest")


def test_ensure_docker_image_source_platform_compares_case_insensitively(
    monkeypatch,
):
    def fake_run(args, check, stdout, stderr, text):
        assert args[:4] == ["docker", "image", "inspect", "--format"]
        return subprocess.CompletedProcess(args, 0, stdout="linux/amd64\n", stderr="")

    monkeypatch.setattr(image_build.subprocess, "run", fake_run)

    image_build._ensure_docker_image_source_platform("local/app:latest", "Linux/AMD64")


def test_package_docker_container_reaps_export_process_on_read_failure(
    monkeypatch,
    tmp_path,
):
    removed = []

    class BrokenStdout:
        def __init__(self):
            self.closed = False

        def read(self, size):
            raise RuntimeError("read failed")

        def close(self):
            self.closed = True

    class FakeProcess:
        def __init__(self):
            self.stdout = BrokenStdout()
            self.terminated = False
            self.killed = False
            self.waits = 0
            self.return_code = None

        def poll(self):
            return self.return_code

        def terminate(self):
            self.terminated = True
            self.return_code = -15

        def kill(self):
            self.killed = True
            self.return_code = -9

        def wait(self, timeout=None):
            self.waits += 1
            if self.return_code is None:
                self.return_code = 0
            return self.return_code

    fake_process = FakeProcess()

    def fake_popen(args, stdout, stderr):
        return fake_process

    monkeypatch.setattr(image_build.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(image_build, "_remove_docker_container", removed.append)

    with pytest.raises(RuntimeError, match="read failed"):
        image_build._package_docker_container(
            "local/app:latest",
            "container-123",
            {},
            platform="linux/amd64",
            temp_dir=str(tmp_path),
        )

    assert fake_process.stdout.closed is True
    assert fake_process.terminated is True
    assert fake_process.killed is False
    assert fake_process.waits == 1
    assert removed == ["container-123"]


def test_upload_image_build_artifact_streams_file_with_content_length(
    monkeypatch,
    tmp_path,
):
    artifact = tmp_path / "rootfs.tar.gz"
    artifact.write_bytes(b"compressed-rootfs")
    calls = []

    def fake_request(method, url, content, headers, timeout):
        calls.append(
            {
                "method": method,
                "url": url,
                "body": content.read(),
                "headers": headers,
                "timeout": timeout,
            }
        )
        return httpx.Response(200, request=httpx.Request(method, url))

    monkeypatch.setattr(image_build.httpx, "request", fake_request)

    image_build.upload_image_build_artifact(
        SandboxImageBuildUpload(
            url="https://upload.example.com/rootfs",
            method="PUT",
            headers={"x-upload": "yes"},
            objectKey="input/key",
            expiresInSeconds=900,
            maxUploadBytes=1000,
        ),
        str(artifact),
        timeout=None,
    )

    assert calls == [
        {
            "method": "PUT",
            "url": "https://upload.example.com/rootfs",
            "body": b"compressed-rootfs",
            "headers": {
                "x-upload": "yes",
                "content-length": str(len(b"compressed-rootfs")),
            },
            "timeout": None,
        }
    ]


def test_upload_image_build_artifact_retries_retryable_status(monkeypatch, tmp_path):
    artifact = tmp_path / "layer.tar"
    artifact.write_bytes(b"layer")
    statuses = iter([500, 200])
    calls = []

    def fake_request(method, url, content, headers, timeout):
        status = next(statuses)
        calls.append(status)
        return httpx.Response(status, request=httpx.Request(method, url))

    monkeypatch.setattr(image_build.httpx, "request", fake_request)
    monkeypatch.setattr(image_build.time, "sleep", lambda seconds: None)

    image_build.upload_image_build_artifact(
        SandboxImageBuildUpload(
            sha256="a" * 64,
            url="https://upload.example.com/layer",
            method="PUT",
            headers={},
            objectKey="layers/a",
            expiresInSeconds=900,
            maxUploadBytes=1000,
        ),
        str(artifact),
    )

    assert calls == [500, 200]


def test_remote_dockerfile_context_is_deterministic_and_sparse(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.12\nCOPY requirements.txt /app/\nCOPY src /app/src\n"
    )
    (tmp_path / ".dockerignore").write_text("ignored.txt\n")
    (tmp_path / "requirements.txt").write_text("httpx\n")
    (tmp_path / "ignored.txt").write_text("not uploaded\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n")

    first = image_build.package_docker_build_context_manifest(tmp_path)
    second = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        assert first.manifest.context_mode == "sparse"
        assert first.artifact.sha256_hex == second.artifact.sha256_hex
        assert sorted(first.bundles) == sorted(second.bundles)

        archived_names = set()
        for artifact in first.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                archived_names.update(name.rstrip("/") for name in archive.getnames())
        assert {
            "Dockerfile",
            ".dockerignore",
            "requirements.txt",
            "src",
            "src/app.py",
        } <= archived_names
        assert "ignored.txt" not in archived_names
    finally:
        first.cleanup()
        second.cleanup()


def test_remote_dockerfile_context_falls_back_for_variable_source(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY $SOURCE /app/\n")
    (tmp_path / "payload.txt").write_text("payload\n")

    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        assert packaged.manifest.context_mode == "full"
        assert packaged.manifest.fallback_reason == "copy_source_requires_expansion"
    finally:
        packaged.cleanup()


def test_remote_dockerfile_context_falls_back_for_source_glob(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY * /app/\n")
    (tmp_path / ".env").write_text("SECRET=not-a-real-secret\n")

    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        assert packaged.manifest.context_mode == "full"
        assert packaged.manifest.fallback_reason == "dockerfile_source_pattern"
        archived_names = set()
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                archived_names.update(name.rstrip("/") for name in archive.getnames())
        assert ".env" in archived_names
    finally:
        packaged.cleanup()


def test_remote_context_prunes_ignored_directories_without_negations(
    monkeypatch, tmp_path
):
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY . /app/\n")
    (tmp_path / ".dockerignore").write_text("node_modules\n")
    (tmp_path / "included.txt").write_text("included\n")
    (tmp_path / "node_modules" / "nested").mkdir(parents=True)
    (tmp_path / "node_modules" / "nested" / "package.js").write_text("ignored\n")

    original_scandir = os.scandir
    walked_context_paths = []
    context_root = os.fspath(tmp_path)

    def tracking_scandir(path):
        if isinstance(path, (str, bytes, os.PathLike)):
            raw_path = os.fspath(path)
            if isinstance(raw_path, str) and (
                raw_path == context_root
                or raw_path.startswith(f"{context_root}{os.sep}")
            ):
                walked_context_paths.append(os.path.relpath(raw_path, context_root))
        return original_scandir(path)

    monkeypatch.setattr(image_build.os, "scandir", tracking_scandir)
    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        archived_names = set()
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                archived_names.update(name.rstrip("/") for name in archive.getnames())
        assert "included.txt" in archived_names
        assert not any(name.startswith("node_modules") for name in archived_names)
        assert "node_modules" not in walked_context_paths
    finally:
        packaged.cleanup()


def test_remote_context_preserves_negated_descendant(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY . /app/\n")
    (tmp_path / ".dockerignore").write_text("node_modules\n!node_modules/keep.txt\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "keep.txt").write_text("keep\n")
    (tmp_path / "node_modules" / "drop.txt").write_text("drop\n")

    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        archived_names = set()
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                archived_names.update(name.rstrip("/") for name in archive.getnames())
        assert "node_modules/keep.txt" in archived_names
        assert "node_modules/drop.txt" not in archived_names
    finally:
        packaged.cleanup()


def test_remote_context_honors_dockerfile_specific_ignore_rules(tmp_path):
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "Buildfile").write_text(
        "FROM scratch\nCOPY src/*.js /app/\nCOPY assets /assets\n"
    )
    (tmp_path / ".dockerignore").write_text("src\nassets\n")
    (tmp_path / "docker" / "Buildfile.dockerignore").write_text(
        "src/*\n!src/keep.js\nassets/private\n"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.js").write_text("keep\n")
    (tmp_path / "src" / "drop.js").write_text("drop\n")
    (tmp_path / "assets" / "private").mkdir(parents=True)
    (tmp_path / "assets" / "public.txt").write_text("public\n")
    (tmp_path / "assets" / "private" / "secret").write_text("secret\n")

    packaged = image_build.package_docker_build_context_manifest(
        tmp_path, dockerfile="docker/Buildfile"
    )
    try:
        archived_names = set()
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                archived_names.update(name.rstrip("/") for name in archive.getnames())
        assert packaged.manifest.context_mode == "full"
        assert {
            "docker/Buildfile",
            "docker/Buildfile.dockerignore",
            "src/keep.js",
            "assets/public.txt",
        } <= archived_names
        assert "src/drop.js" not in archived_names
        assert "assets/private/secret" not in archived_names
    finally:
        packaged.cleanup()


def test_remote_context_sparse_source_includes_symlink_target_closure(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "FROM scratch\nCOPY alias/data.txt /app/data.txt\n"
    )
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "data.txt").write_text("selected\n")
    (tmp_path / "real" / "unreferenced.txt").write_text("not selected\n")
    (tmp_path / "alias").symlink_to("real")

    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        headers = {}
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                headers.update(
                    {member.name.rstrip("/"): member for member in archive.getmembers()}
                )

        assert packaged.manifest.context_mode == "sparse"
        assert headers["alias"].issym()
        assert headers["alias"].linkname == "real"
        assert headers["real"].isdir()
        assert headers["real/data.txt"].isfile()
        assert "real/unreferenced.txt" not in headers
    finally:
        packaged.cleanup()


def test_remote_context_includes_ignored_symlink_dockerfile_target(tmp_path):
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "ActualDockerfile").write_text(
        "FROM scratch\nCOPY app /app\n"
    )
    (tmp_path / "Dockerfile").symlink_to("docker/ActualDockerfile")
    (tmp_path / ".dockerignore").write_text("docker\n")
    (tmp_path / "app").write_text("payload\n")

    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        names = set()
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                names.update(member.name.rstrip("/") for member in archive.getmembers())

        assert {"Dockerfile", "docker", "docker/ActualDockerfile", "app"} <= names
    finally:
        packaged.cleanup()


def test_remote_context_preserves_external_and_broken_symlink_metadata(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY links /links\n")
    (tmp_path / "links").mkdir()
    (tmp_path / "links" / "relative").symlink_to("../../outside")
    (tmp_path / "links" / "absolute").symlink_to("/etc/passwd")
    (tmp_path / "links" / "broken link").symlink_to("missing target")

    packaged = image_build.package_docker_build_context_manifest(tmp_path)
    try:
        symlinks = {}
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path, "r:gz") as archive:
                symlinks.update(
                    {
                        member.name: member.linkname
                        for member in archive.getmembers()
                        if member.issym()
                    }
                )

        assert symlinks == {
            "links/absolute": "/etc/passwd",
            "links/broken link": "missing target",
            "links/relative": "../../outside",
        }
    finally:
        packaged.cleanup()


def test_package_docker_image_manifest_preserves_reusable_layers(
    monkeypatch,
    tmp_path,
):
    config_bytes = b'{"architecture":"amd64","config":{}}'
    layer_bytes = b"reusable-layer-tar"
    save_manifest = json.dumps(
        [{"Config": "config.json", "Layers": ["layer.tar"]}],
        separators=(",", ":"),
    ).encode()
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
        for name, data in (
            ("config.json", config_bytes),
            ("layer.tar", layer_bytes),
            ("manifest.json", save_manifest),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    archive_bytes = archive_buffer.getvalue()

    class FakeProcess:
        def __init__(self):
            self.stdout = io.BytesIO(archive_bytes)
            self.return_code = None

        def poll(self):
            return self.return_code

        def wait(self, timeout=None):
            self.return_code = 0
            return 0

        def terminate(self):
            self.return_code = -15

        def kill(self):
            self.return_code = -9

    monkeypatch.setattr(
        image_build.subprocess, "Popen", lambda *args, **kwargs: FakeProcess()
    )
    config_sha = hashlib.sha256(config_bytes).hexdigest()

    packaged = image_build.package_docker_image_manifest(
        "local/app:latest",
        f"sha256:{config_sha}",
        {"User": "node"},
        temp_dir=str(tmp_path),
    )
    try:
        layer_sha = hashlib.sha256(layer_bytes).hexdigest()
        assert packaged.artifact.input_format == "docker_image_manifest_v1"
        assert packaged.manifest.image_digest == f"sha256:{config_sha}"
        assert packaged.manifest.config.sha256 == config_sha
        assert [layer.sha256 for layer in packaged.manifest.layers] == [layer_sha]
        assert open(packaged.layers[layer_sha].path, "rb").read() == layer_bytes
    finally:
        packaged.cleanup()


def test_sync_dockerfile_build_uses_remote_context_by_default(monkeypatch, tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    manager = SandboxManager(
        SimpleNamespace(timeout=30, config=SimpleNamespace(runtime_proxy_override=None))
    )
    captured = []
    monkeypatch.setattr(
        manager,
        "create_image_build",
        lambda params: (
            captured.append(params)
            or SandboxImageBuildCreateResult(
                build=_image_build("awaiting_upload"),
                uploads=[],
            )
        ),
    )
    monkeypatch.setattr(
        manager,
        "_complete_image_build_resilient",
        lambda build_id, artifact: _image_build("dispatching"),
    )
    monkeypatch.setattr(
        sync_sandbox_module,
        "build_docker_image_from_dockerfile",
        lambda **kwargs: pytest.fail("remote build unexpectedly invoked local Docker"),
    )

    result = manager.build_image_from_dockerfile(
        context_path=tmp_path,
        image_name="custom",
        wait=False,
    )

    assert result.status == "dispatching"
    assert captured[0].input_format == "dockerfile_context_manifest_v1"
    assert captured[0].dockerfile_path == "Dockerfile"
    assert captured[0].context_manifest.context_mode == "sparse"


def test_sync_docker_image_exact_reuse_skips_docker_save(monkeypatch):
    cleaned = []
    source = image_build.DockerImageManifestSource(
        image_digest="sha256:" + "a" * 64,
        config={
            "User": "node",
            "Env": ["APP_ENV=prod"],
            "Entrypoint": ["node"],
            "Cmd": ["server.js"],
            "WorkingDir": "/app",
        },
        cleanup_callback=lambda: cleaned.append(True),
    )
    monkeypatch.setattr(
        sync_sandbox_module,
        "prepare_docker_image_manifest_source",
        lambda *args, **kwargs: source,
    )
    monkeypatch.setattr(
        sync_sandbox_module,
        "package_docker_image_manifest",
        lambda *args, **kwargs: pytest.fail("cache hit unexpectedly ran docker save"),
    )
    manager = SandboxManager(
        SimpleNamespace(timeout=30, config=SimpleNamespace(runtime_proxy_override=None))
    )
    reused = []
    monkeypatch.setattr(
        manager,
        "reuse_docker_image",
        lambda params: (
            reused.append(params)
            or SimpleNamespace(hit=True, build=_image_build("completed"))
        ),
    )

    result = manager.build_image_from_docker_image(
        docker_image="local/app:latest",
        image_name="custom",
        image_init={"env": {"APP_ENV": "test"}, "working_dir": "/srv"},
    )

    assert result.status == "completed"
    assert reused[0].source_image_digest == "sha256:" + "a" * 64
    assert reused[0].image_config_user == "node"
    assert reused[0].image_init.env == {"APP_ENV": "test"}
    assert reused[0].image_init.args == ["node", "server.js"]
    assert reused[0].image_init.working_dir == "/srv"
    assert cleaned == [True]


def test_sync_dockerfile_image_build_cleans_temp_tag_on_build_failure(monkeypatch):
    removed = []

    def fake_build(**kwargs):
        raise RuntimeError("build failed")

    monkeypatch.setattr(sync_sandbox_module, "make_temp_docker_tag", lambda: "temp:tag")
    monkeypatch.setattr(
        sync_sandbox_module,
        "build_docker_image_from_dockerfile",
        fake_build,
    )
    monkeypatch.setattr(sync_sandbox_module, "remove_docker_image", removed.append)

    manager = SandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )

    with pytest.raises(RuntimeError, match="build failed"):
        manager.build_image_from_dockerfile(
            context_path=".",
            image_name="custom",
            remote=False,
        )

    assert removed == ["temp:tag"]


def test_sync_wait_for_image_build_returns_completed_status(monkeypatch):
    manager = SandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )
    monkeypatch.setattr(
        manager,
        "get_image_build",
        lambda build_id: _image_build("completed"),
    )

    build = manager.wait_for_image_build("build-123", poll_interval=0, timeout=1)

    assert build.status == "completed"


def test_sync_wait_for_image_build_raises_detailed_failed_status(monkeypatch):
    manager = SandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )
    monkeypatch.setattr(
        manager,
        "get_image_build",
        lambda build_id: _image_build(
            "failed",
            error_code="E_BAD",
            error_message="backend failure",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=r"image build failed \[E_BAD\]: backend failure",
    ):
        manager.wait_for_image_build("build-123", poll_interval=0, timeout=1)


def test_sync_complete_image_build_retries_upload_verification_race(monkeypatch):
    manager = SandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )
    calls = []

    def fake_complete(build_id, params):
        calls.append((build_id, params))
        if len(calls) == 1:
            raise HyperbrowserError("upload verification pending", status_code=409)
        return _image_build("dispatching")

    monkeypatch.setattr(manager, "complete_image_build", fake_complete)
    monkeypatch.setattr(
        manager,
        "get_image_build",
        lambda build_id: _image_build("upload_verified"),
    )
    monkeypatch.setattr(sync_sandbox_module.time, "sleep", lambda seconds: None)
    artifact = image_build.DockerImageBuildArtifact(
        path="unused",
        sha256_hex="a" * 64,
        size_bytes=123,
        input_format="docker_image_manifest_v1",
    )

    result = manager._complete_image_build_resilient("build-123", artifact)

    assert result.status == "dispatching"
    assert len(calls) == 2


@pytest.mark.anyio
async def test_async_dockerfile_image_build_cleans_temp_tag_on_build_failure(
    monkeypatch,
):
    removed = []

    def fake_build(**kwargs):
        raise RuntimeError("build failed")

    monkeypatch.setattr(
        async_sandbox_module,
        "make_temp_docker_tag",
        lambda: "temp:tag",
    )
    monkeypatch.setattr(
        async_sandbox_module,
        "build_docker_image_from_dockerfile",
        fake_build,
    )
    monkeypatch.setattr(async_sandbox_module, "remove_docker_image", removed.append)

    manager = AsyncSandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )

    with pytest.raises(RuntimeError, match="build failed"):
        await manager.build_image_from_dockerfile(
            context_path=".",
            image_name="custom",
            remote=False,
        )

    assert removed == ["temp:tag"]


@pytest.mark.anyio
async def test_async_wait_for_image_build_returns_completed_status(monkeypatch):
    manager = AsyncSandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )

    async def fake_get_image_build(build_id):
        return _image_build("completed")

    monkeypatch.setattr(manager, "get_image_build", fake_get_image_build)

    build = await manager.wait_for_image_build(
        "build-123",
        poll_interval=0,
        timeout=1,
    )

    assert build.status == "completed"


@pytest.mark.anyio
async def test_async_wait_for_image_build_raises_detailed_failed_status(monkeypatch):
    manager = AsyncSandboxManager(
        SimpleNamespace(
            timeout=30,
            config=SimpleNamespace(runtime_proxy_override=None),
        )
    )

    async def fake_get_image_build(build_id):
        return _image_build(
            "failed",
            error_code="E_BAD",
            error_message="backend failure",
        )

    monkeypatch.setattr(manager, "get_image_build", fake_get_image_build)

    with pytest.raises(
        RuntimeError,
        match=r"image build failed \[E_BAD\]: backend failure",
    ):
        await manager.wait_for_image_build(
            "build-123",
            poll_interval=0,
            timeout=1,
        )
