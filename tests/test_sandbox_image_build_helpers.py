import subprocess
from types import SimpleNamespace

import httpx
import pytest

import hyperbrowser.client.managers.async_manager.sandbox as async_sandbox_module
import hyperbrowser.client.managers.sync_manager.sandbox as sync_sandbox_module
from hyperbrowser.client.managers.sandboxes import image_build
from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxManager as AsyncSandboxManager,
)
from hyperbrowser.client.managers.sync_manager.sandbox import SandboxManager
from hyperbrowser.models import SandboxImageBuildUpload


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
        )

    assert removed == ["temp:tag"]


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
        )

    assert removed == ["temp:tag"]
