import asyncio
import gzip
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path

import httpx
import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.build_context import (
    DockerBuildContextChangedError,
    docker_build_context_fingerprint,
)
from hyperbrowser.client.managers.sandboxes import image_build
from hyperbrowser.models import SandboxImageSummary


def context(root, dockerfile="FROM scratch\nCOPY . /app\n", ignore=""):
    root.mkdir(exist_ok=True)
    (root / "Dockerfile").write_text(dockerfile)
    (root / ".dockerignore").write_text(ignore)
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text("print('hello')\n")
    (root / "app" / "debug.log").write_text("diagnostics\n")
    (root / "unused").write_text("not copied by sparse builds\n")
    return root


def test_fingerprint_format_is_stable_across_python_versions(tmp_path):
    (tmp_path / "Dockerfile").write_bytes(b"FROM scratch\nCOPY . /app\n")
    (tmp_path / "Dockerfile").chmod(0o644)
    folder = tmp_path / ("long-path-" + "x" * 110)
    folder.mkdir()
    folder.chmod(0o755)
    (folder / "unicode-ü.txt").write_bytes(b"canonical\x00payload\n")
    (folder / "unicode-ü.txt").chmod(0o640)
    (tmp_path / "empty").write_bytes(b"")
    (tmp_path / "empty").chmod(0o600)
    (tmp_path / "link").symlink_to("empty")
    assert docker_build_context_fingerprint(tmp_path) == (
        "8d66062b58007e23ed8844b026726ac24e4ea5b32e4d6c3e4590d48b252755f9"
    )


@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize(
    "dockerfile,ignore",
    [
        ("FROM scratch\nCOPY app /app\n", ""),
        ("FROM scratch\nCOPY . /app\n", "**/*.log\n"),
        ("FROM scratch\nCOPY . /app\n", "app\n!app/main.py\n"),
        ("FROM scratch\nCOPY app /app\nCOPY app/main.py /main\n", ""),
        ("FROM scratch\nCOPY app/*.py /app/\n", "unused\n"),
        ("FROM scratch\nARG SRC=app\nCOPY $SRC /app\n", ""),
        ("FROM scratch\n", "*\n"),
        (
            "FROM scratch AS source\nCOPY app /app\nFROM scratch\nCOPY --from=source /app /app\n",
            "",
        ),
        (
            "FROM busybox\nRUN --mount=type=bind,source=app,target=/app cat /app/main.py\n",
            "",
        ),
        ("FROM busybox\nRUN --mount=type=bind,source=$DIR,target=/app true\n", ""),
        ("FROM scratch\nCOPY <<EOF /hello\nhello\nEOF\n", ""),
        ("FROM scratch\nCOPY --chmod=0755 --link app /app\n", ""),
        ("FROM scratch\nADD app /app\n", ""),
        ("# syntax=custom/frontend:1\nFROM scratch\n", ""),
    ],
)
def test_fingerprint_matches_bytes_in_actual_archives(
    tmp_path, full, dockerfile, ignore
):
    root = context(tmp_path / "context", dockerfile, ignore)
    expected = docker_build_context_fingerprint(root, force_full_context=full)
    packaged = image_build.package_docker_build_context_manifest(
        root, force_full_context=full, expected_context_fingerprint=expected
    )
    try:
        hashes = []
        for artifact in packaged.bundles.values():
            hasher = hashlib.sha256()
            with tarfile.open(artifact.path) as archive:
                for info in archive:
                    assert info.uid == info.gid == info.mtime == 0
                    metadata = json.dumps(
                        [
                            info.name,
                            "file"
                            if info.isfile()
                            else "directory"
                            if info.isdir()
                            else "symlink",
                            info.mode,
                            info.size,
                            info.linkname,
                        ],
                        separators=(",", ":"),
                    ).encode()
                    hasher.update(len(metadata).to_bytes(8, "big"))
                    hasher.update(metadata)
                    if info.isfile():
                        hasher.update(archive.extractfile(info).read())
            hashes.append(hasher.hexdigest())
        identity = {
            "version": 1,
            "dockerfile": packaged.manifest.dockerfile_path,
            "contextMode": packaged.manifest.context_mode,
            "bundles": sorted(set(hashes)),
        }
        actual = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert expected == actual == packaged.fingerprint
    finally:
        packaged.cleanup()


@pytest.mark.parametrize(
    "change,changes_identity",
    [
        ("contents", True),
        ("same-size-contents", True),
        ("mode", True),
        ("path", True),
        ("mtime", False),
        ("ignored-file", False),
        ("ignored-tree", False),
        ("unused-file", False),
        ("unused-empty-directory", False),
        ("dockerfile", True),
        ("ignore-rules", True),
        ("symlink", True),
        ("symlink-target-contents", True),
        ("included-empty-directory", True),
    ],
)
def test_identity_tracks_effective_build_inputs(tmp_path, change, changes_identity):
    root = context(
        tmp_path,
        "FROM scratch\nCOPY app /app\nCOPY link /link\n",
        "**/*.log\napp/cache\n",
    )
    target = root / "target"
    target.write_text("one\n")
    (root / "other").write_text("one\n")
    (root / "link").symlink_to("target")
    (root / "app" / "cache").mkdir()
    script = root / "app" / "main.py"
    before = docker_build_context_fingerprint(root)
    if change == "contents":
        script.write_text("new program\n")
    elif change == "same-size-contents":
        script.write_text(script.read_text().replace("hello", "world"))
    elif change == "mode":
        script.chmod(0o755)
    elif change == "path":
        script.rename(root / "app" / "renamed.py")
    elif change == "mtime":
        os.utime(script, (100, 100))
    elif change == "ignored-file":
        (root / "app" / "debug.log").write_text("changed\n")
    elif change == "ignored-tree":
        (root / "app" / "cache" / "new-file").write_text("ignored\n")
    elif change == "unused-file":
        (root / "unused").write_text("changed\n")
    elif change == "unused-empty-directory":
        (root / "empty").mkdir()
    elif change == "dockerfile":
        with (root / "Dockerfile").open("a") as stream:
            stream.write("ENV CHANGED=yes\n")
    elif change == "ignore-rules":
        (root / ".dockerignore").write_text("**/*.log\napp/main.py\n")
    elif change == "symlink":
        (root / "link").unlink()
        (root / "link").symlink_to("other")
    elif change == "symlink-target-contents":
        target.write_text("two\n")
    elif change == "included-empty-directory":
        (root / "app" / "empty").mkdir()
    after = docker_build_context_fingerprint(root)
    assert (before != after) is changes_identity
    packaged = image_build.package_docker_build_context_manifest(
        root, expected_context_fingerprint=after
    )
    try:
        assert packaged.fingerprint == after
    finally:
        packaged.cleanup()


def test_dockerfile_specific_ignore_and_ignored_control_files(tmp_path):
    root = context(tmp_path, "FROM scratch\nCOPY app /app\n")
    (root / "Dockerfile.dockerignore").write_text("*\n!app/main.py\n")
    before = docker_build_context_fingerprint(root)
    (root / ".dockerignore").write_text("app/main.py\n")
    (root / "app" / "debug.log").write_text("ignored\n")
    assert docker_build_context_fingerprint(root) == before
    (root / "Dockerfile.dockerignore").write_text("*\n!app/debug.log\n")
    assert docker_build_context_fingerprint(root) != before


def test_identity_is_independent_of_absolute_path_and_compression(
    tmp_path, monkeypatch
):
    first = context(tmp_path / "first")
    second = tmp_path / "second"
    shutil.copytree(first, second)
    expected = docker_build_context_fingerprint(first)
    assert docker_build_context_fingerprint(second) == expected
    original_gzip = gzip.GzipFile

    def different_compression(**kwargs):
        kwargs["compresslevel"] = 9
        return original_gzip(**kwargs)

    monkeypatch.setattr(gzip, "GzipFile", different_compression)
    packaged = image_build.package_docker_build_context_manifest(
        second, expected_context_fingerprint=expected
    )
    packaged.cleanup()


def test_fingerprint_never_compresses_stages_or_reads_whole_payload(
    tmp_path, monkeypatch
):
    root = context(tmp_path)
    original_read = Path.read_bytes

    def read_bytes(path):
        assert path.name in ("Dockerfile", ".dockerignore"), "payloads must be streamed"
        return original_read(path)

    def forbidden(*args, **kwargs):
        pytest.fail("cache fingerprint must not compress or create a workspace")

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(image_build.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(gzip, "GzipFile", forbidden)
    assert len(docker_build_context_fingerprint(root)) == 64


@pytest.mark.parametrize("full", [False, True])
def test_hard_links_preserve_all_paths_and_match_independent_copies(tmp_path, full):
    root = context(tmp_path / "linked", "FROM scratch\nCOPY app /app\n")
    first = root / "app" / "main.py"
    second = root / "app" / "second.py"
    os.link(first, second)
    # A symbolic link must remain a link; dereferencing all links is not a fix.
    (root / "app" / "link").symlink_to("main.py")
    copied = tmp_path / "copied"
    shutil.copytree(root, copied, symlinks=True)
    expected = docker_build_context_fingerprint(root, force_full_context=full)
    assert docker_build_context_fingerprint(copied, force_full_context=full) == expected
    packaged = image_build.package_docker_build_context_manifest(
        root, force_full_context=full, expected_context_fingerprint=expected
    )
    try:
        files = {}
        for artifact in packaged.bundles.values():
            with tarfile.open(artifact.path) as archive:
                for info in archive:
                    if info.isfile():
                        files[info.name] = archive.extractfile(info).read()
                    if info.name == "app/link":
                        assert info.issym() and info.linkname == "main.py"
        assert files["app/main.py"] == files["app/second.py"] == first.read_bytes()
    finally:
        packaged.cleanup()
    second.write_text("updated through hard link\n")
    assert docker_build_context_fingerprint(root, force_full_context=full) != expected


@pytest.mark.parametrize("during_packaging", [False, True])
def test_mutation_rejected_using_archived_bytes_and_workspace_removed(
    tmp_path, monkeypatch, during_packaging
):
    root = context(tmp_path / "context")
    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    expected = docker_build_context_fingerprint(root)
    script = root / "app" / "main.py"
    original = script.read_bytes()
    original_addfile = tarfile.TarFile.addfile

    def addfile(archive, info, fileobj=None):
        if info.name == "app/main.py":
            # Change while packaging, then restore before it returns. A second
            # filesystem hash would miss this; hashing archived bytes must not.
            script.write_bytes(b"x" * len(original))
            try:
                return original_addfile(archive, info, fileobj)
            finally:
                script.write_bytes(original)
        return original_addfile(archive, info, fileobj)

    if during_packaging:
        monkeypatch.setattr(tarfile.TarFile, "addfile", addfile)
    else:
        script.write_bytes(b"x" * len(original))
    with pytest.raises(DockerBuildContextChangedError, match="changed.*fingerprint"):
        image_build.package_docker_build_context_manifest(
            root, temp_dir=str(workspaces), expected_context_fingerprint=expected
        )
    assert list(workspaces.iterdir()) == []


@pytest.mark.parametrize("invalid", ["", "a" * 63, "A" * 64, "g" * 64])
def test_invalid_expected_fingerprints_are_rejected_before_packaging(tmp_path, invalid):
    with pytest.raises(ValueError, match="SHA-256 hex digest"):
        image_build.package_docker_build_context_manifest(
            tmp_path / "missing-context", expected_context_fingerprint=invalid
        )


@pytest.mark.parametrize("asynchronous", [False, True])
def test_expected_fingerprint_cannot_be_silently_ignored_by_local_build(asynchronous):
    kwargs = dict(
        context_path=".",
        image_name="local",
        remote=False,
        expected_context_fingerprint="a" * 64,
    )
    if asynchronous:

        async def run():
            async with AsyncHyperbrowser(api_key="test") as client:
                await client.sandboxes.build_image_from_dockerfile(**kwargs)

        with pytest.raises(ValueError, match="requires remote=True"):
            asyncio.run(run())
    else:
        client = Hyperbrowser(api_key="test")
        try:
            with pytest.raises(ValueError, match="requires remote=True"):
                client.sandboxes.build_image_from_dockerfile(**kwargs)
        finally:
            client.close()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("changed", [False, True])
def test_public_build_checks_fingerprint_before_any_api_request(
    tmp_path, monkeypatch, asynchronous, changed
):
    root = context(tmp_path / "context")
    expected = docker_build_context_fingerprint(root)
    if changed:
        (root / "app" / "main.py").write_text("new bytes\n")
    requests = []

    def respond(request):
        requests.append(request)
        assert not changed, "changed inputs must fail before submitting a build"
        build = {"id": "build", "imageName": "cached", "status": "awaiting_upload"}
        if request.url.path.endswith("/complete"):
            return httpx.Response(200, json={"build": {**build, "status": "building"}})
        return httpx.Response(200, json={"build": build, "uploads": []})

    kwargs = dict(
        context_path=root,
        image_name="cached",
        expected_context_fingerprint=expected,
        wait=False,
    )
    if asynchronous:
        original = httpx.AsyncClient
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda **kw: original(transport=httpx.MockTransport(respond), **kw),
        )

        async def run():
            async with AsyncHyperbrowser(
                api_key="test", base_url="http://local.test"
            ) as client:
                return await client.sandboxes.build_image_from_dockerfile(**kwargs)

        def call():
            return asyncio.run(run())
    else:
        original = httpx.Client
        monkeypatch.setattr(
            httpx,
            "Client",
            lambda **kw: original(transport=httpx.MockTransport(respond), **kw),
        )

        def call():
            client = Hyperbrowser(api_key="test", base_url="http://local.test")
            try:
                return client.sandboxes.build_image_from_dockerfile(**kwargs)
            finally:
                client.close()

    if changed:
        with pytest.raises(DockerBuildContextChangedError):
            call()
        assert requests == []
    else:
        assert call().status == "building"
        assert len(requests) == 2
        assert "expected_context_fingerprint" not in json.loads(requests[0].content)


@pytest.mark.parametrize("ready", [None, False, True])
@pytest.mark.parametrize("uploaded", [False, True])
def test_image_readiness_is_independent_of_backup_and_backward_compatible(
    ready, uploaded
):
    payload = dict(
        id="image",
        imageName="cached",
        namespace="team_test",
        uploaded=uploaded,
        createdAt="2026-01-01T00:00:00Z",
        updatedAt="2026-01-01T00:00:00Z",
    )
    if ready is not None:
        payload["ready"] = ready
    image = SandboxImageSummary(**payload)
    assert image.ready is ready
    assert image.uploaded is uploaded
