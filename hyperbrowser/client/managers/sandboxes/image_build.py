import base64
import glob
import gzip
import hashlib
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple

import httpx
from pathspec import PathSpec

from ....models.sandbox import (
    SandboxBuildContextBundle,
    SandboxBuildContextManifest,
    SandboxDockerImageConfig,
    SandboxDockerImageLayer,
    SandboxDockerImageManifest,
    SandboxImageBuildInputFormat,
    SandboxImageBuildStatus,
    SandboxImageBuildUpload,
    SandboxImageInit,
)

IMAGE_BUILD_INPUT_FORMAT: SandboxImageBuildInputFormat = "rootfs_export_tar_gz"
CONTEXT_MANIFEST_INPUT_FORMAT: SandboxImageBuildInputFormat = (
    "dockerfile_context_manifest_v1"
)
DOCKER_IMAGE_MANIFEST_INPUT_FORMAT: SandboxImageBuildInputFormat = (
    "docker_image_manifest_v1"
)
IMAGE_BUILD_SOURCE_PLATFORM = "linux/amd64"
TERMINAL_IMAGE_BUILD_STATUSES: FrozenSet[SandboxImageBuildStatus] = frozenset(
    {"completed", "failed", "canceled"}
)
_IMAGE_INIT_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RESERVED_IMAGE_INIT_ENV_KEYS = {
    "SANDBOX_ENABLED",
    "SANDBOX_DEFAULT_WORKING_DIR",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "PATH",
    "PWD",
    "DISPLAY",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_CONTEXT_SOURCE_GROUPS = 511
_MAX_CONTEXT_ENTRIES = 1_000_000
_MAX_DOCKER_SAVE_ENTRIES = 4096
_MAX_DOCKER_SAVE_ARCHIVE_BYTES = 5 * 1024 * 1024 * 1024
_MAX_DOCKER_SAVE_METADATA_BYTES = 16 * 1024 * 1024
_MAX_DOCKER_IMAGE_LAYERS = 512


@dataclass
class DockerImageBuildArtifact:
    path: str
    sha256_hex: str
    size_bytes: int
    input_format: SandboxImageBuildInputFormat
    source_platform: str = IMAGE_BUILD_SOURCE_PLATFORM
    image_config_user: str = ""
    image_init: Optional[SandboxImageInit] = None

    def cleanup(self) -> None:
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


@dataclass
class PackagedDockerBuildContext:
    artifact: DockerImageBuildArtifact
    manifest: SandboxBuildContextManifest
    bundles: Dict[str, DockerImageBuildArtifact]
    workspace: str

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


@dataclass
class DockerImageManifestSource:
    image_digest: str
    config: Dict[str, object]
    cleanup_callback: Callable[[], None]

    @property
    def image_config_user(self) -> str:
        return str(self.config.get("User") or "").strip()

    @property
    def image_init(self) -> Optional[SandboxImageInit]:
        return _derive_auto_image_init(self.config)

    def cleanup(self) -> None:
        self.cleanup_callback()


@dataclass
class PackagedDockerImage:
    artifact: DockerImageBuildArtifact
    manifest: SandboxDockerImageManifest
    layers: Dict[str, DockerImageBuildArtifact]
    workspace: str

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


@dataclass
class _StoredDockerSaveEntry:
    path: str
    sha256_hex: str
    size_bytes: int


class _HashingCountingWriter:
    def __init__(self, fileobj, hasher):
        self._fileobj = fileobj
        self._hasher = hasher
        self.total = 0

    def write(self, data):
        self._hasher.update(data)
        self.total += len(data)
        return self._fileobj.write(data)

    def flush(self):
        return self._fileobj.flush()


def build_docker_image_from_dockerfile(
    *,
    context_path,
    dockerfile="Dockerfile",
    tag: str,
    platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
    build_args: Optional[Dict[str, str]] = None,
) -> None:
    context = Path(context_path)
    if not context.exists():
        raise FileNotFoundError(f"Docker build context not found: {context}")
    dockerfile_path = Path(dockerfile)
    if not dockerfile_path.is_absolute():
        dockerfile_path = context / dockerfile_path

    args = [
        "docker",
        "buildx",
        "build",
        "--platform",
        platform,
        "-t",
        tag,
        "-f",
        str(dockerfile_path),
        "--load",
    ]
    for key, value in (build_args or {}).items():
        args.extend(["--build-arg", f"{key}={value}"])
    args.append(str(context))
    _run_command(args)


def package_docker_build_context_manifest(
    context_path,
    *,
    dockerfile="Dockerfile",
    force_full_context: bool = False,
    temp_dir: Optional[str] = None,
) -> PackagedDockerBuildContext:
    context_root = Path(context_path).expanduser().resolve(strict=True)
    if not context_root.is_dir():
        raise ValueError("Docker build context must be a directory")
    dockerfile_relative = _clean_context_relative_path(dockerfile, "Dockerfile")
    dockerfile_path = context_root / Path(dockerfile_relative)
    if not dockerfile_path.is_file() and not dockerfile_path.is_symlink():
        raise ValueError(
            f'Dockerfile "{dockerfile_relative}" must be a regular file or symlink'
        )
    resolved_dockerfile = dockerfile_path.resolve(strict=True)
    if not resolved_dockerfile.is_file() or not _path_is_within(
        context_root, resolved_dockerfile
    ):
        raise ValueError(
            f'Dockerfile "{dockerfile_relative}" must resolve to a regular file '
            "inside the build context"
        )

    dockerfile_bytes = dockerfile_path.read_bytes()
    ignore_relative = _select_dockerignore(context_root, dockerfile_relative)
    ignore_spec = _load_dockerignore(context_root / ignore_relative)
    source_groups, fallback_reason = _analyze_dockerfile_sources(dockerfile_bytes)
    if force_full_context:
        source_groups = []
        fallback_reason = "requested_full_context"
    source_groups = _deduplicate_source_groups(source_groups)
    if len(source_groups) > _MAX_CONTEXT_SOURCE_GROUPS:
        source_groups = []
        fallback_reason = "too_many_context_source_groups"
    if any("." in group for group in source_groups):
        fallback_reason = fallback_reason or ""

    context_mode = (
        "full"
        if fallback_reason or any("." in group for group in source_groups)
        else "sparse"
    )
    control_sources = [dockerfile_relative, ignore_relative]
    resolved_relative = resolved_dockerfile.relative_to(context_root).as_posix()
    control_sources.append(resolved_relative)

    if context_mode == "full":
        entry_groups = [
            _collect_context_entries(
                context_root,
                ["."],
                ignore_spec=ignore_spec,
                required=False,
            )
            | _collect_context_entries(
                context_root,
                control_sources,
                ignore_spec=None,
                required=False,
            )
        ]
    else:
        entry_groups = [
            _collect_context_entries(
                context_root,
                control_sources,
                ignore_spec=None,
                required=False,
            )
        ]
        for group in source_groups:
            entry_groups.append(
                _collect_context_entries(
                    context_root,
                    group,
                    ignore_spec=ignore_spec,
                    required=True,
                )
            )
        if sum(len(entries) for entries in entry_groups) > _MAX_CONTEXT_ENTRIES:
            context_mode = "full"
            fallback_reason = "context_selection_too_large"
            entry_groups = [
                _collect_context_entries(
                    context_root,
                    ["."],
                    ignore_spec=ignore_spec,
                    required=False,
                )
                | _collect_context_entries(
                    context_root,
                    control_sources,
                    ignore_spec=None,
                    required=False,
                )
            ]

    entry_groups = _remove_subsumed_entry_groups(entry_groups)
    workspace = tempfile.mkdtemp(prefix="hb-docker-context-", dir=temp_dir)
    try:
        bundles = {}
        descriptors = []
        for index, entries in enumerate(entry_groups):
            artifact, descriptor = _package_context_bundle(
                context_root,
                sorted(entries),
                workspace,
                index,
            )
            if descriptor.sha256 in bundles:
                artifact.cleanup()
                continue
            bundles[descriptor.sha256] = artifact
            descriptors.append(descriptor)
        descriptors.sort(key=lambda item: item.sha256)
        manifest = SandboxBuildContextManifest(
            version=1,
            dockerfile_path=dockerfile_relative,
            context_mode=context_mode,
            fallback_reason=fallback_reason or None,
            bundles=descriptors,
        )
        manifest_bytes = _canonical_model_json(manifest)
        artifact = _write_manifest_artifact(
            workspace,
            "context-manifest.json",
            manifest_bytes,
            CONTEXT_MANIFEST_INPUT_FORMAT,
        )
        return PackagedDockerBuildContext(
            artifact=artifact,
            manifest=manifest,
            bundles=bundles,
            workspace=workspace,
        )
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise


def prepare_docker_image_manifest_source(
    docker_image: str,
    *,
    platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
) -> DockerImageManifestSource:
    try:
        inspection = _inspect_docker_image(docker_image, platform)
        return DockerImageManifestSource(
            image_digest=_normalize_sha256_digest(inspection.get("Id")),
            config=_require_dict(inspection.get("Config"), "Docker image config"),
            cleanup_callback=lambda: None,
        )
    except RuntimeError:
        container_id = _run_command_output(
            ["docker", "create", f"--platform={platform}", docker_image]
        ).strip()
        if not container_id:
            raise RuntimeError("docker create returned empty container ID")
        try:
            config = _inspect_docker_container_config(container_id)
            try:
                digest = _run_command_output(
                    [
                        "docker",
                        "image",
                        "inspect",
                        f"--platform={platform}",
                        "--format",
                        "{{.Id}}",
                        docker_image,
                    ]
                )
            except RuntimeError:
                digest = _run_command_output(
                    [
                        "docker",
                        "container",
                        "inspect",
                        "--format",
                        "{{.Image}}",
                        container_id,
                    ]
                )
            return DockerImageManifestSource(
                image_digest=_normalize_sha256_digest(digest),
                config=config,
                cleanup_callback=lambda: _remove_docker_container(container_id),
            )
        except Exception:
            _remove_docker_container(container_id)
            raise


def package_docker_image_manifest(
    docker_image: str,
    image_digest: str,
    config: Dict[str, object],
    *,
    platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
    temp_dir: Optional[str] = None,
) -> PackagedDockerImage:
    image_digest = _normalize_sha256_digest(image_digest)
    workspace = tempfile.mkdtemp(prefix="hb-docker-image-layers-", dir=temp_dir)
    stderr_file = tempfile.TemporaryFile()
    process = None
    try:
        process = subprocess.Popen(
            ["docker", "image", "save", f"--platform={platform}", docker_image],
            stdout=subprocess.PIPE,
            stderr=stderr_file,
        )
        if process.stdout is None:
            raise RuntimeError("docker image save did not provide stdout")
        entries = {}
        total_bytes = 0
        with tarfile.open(fileobj=process.stdout, mode="r|*") as archive:
            for index, member in enumerate(archive):
                if index >= _MAX_DOCKER_SAVE_ENTRIES:
                    raise RuntimeError(
                        "docker image save contains more than "
                        f"{_MAX_DOCKER_SAVE_ENTRIES} entries"
                    )
                if not member.isfile():
                    continue
                name = _normalize_docker_save_entry_name(member.name)
                if name in entries:
                    raise RuntimeError(
                        f'docker image save contains duplicate entry "{name}"'
                    )
                total_bytes += member.size
                if member.size < 0 or total_bytes > _MAX_DOCKER_SAVE_ARCHIVE_BYTES:
                    raise RuntimeError(
                        "docker image save archive exceeds the size limit"
                    )
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f'cannot read Docker save entry "{name}"')
                destination = os.path.join(workspace, f"entry-{index:04d}")
                entries[name] = _store_streamed_entry(
                    source,
                    destination,
                    member.size,
                    name,
                )
        return_code = process.wait()
        if return_code != 0:
            stderr_file.seek(0)
            message = stderr_file.read().decode("utf-8", errors="replace").strip()
            if message:
                raise RuntimeError(
                    f"docker image save {docker_image} failed: {message}"
                )
            raise RuntimeError(
                f"docker image save {docker_image} failed with code {return_code}"
            )

        config_entry, layer_entries = _resolve_docker_save_manifest(entries)
        config_bytes = Path(config_entry.path).read_bytes()
        _require_json_object(config_bytes, "Docker image config")
        config_descriptor = SandboxDockerImageConfig(
            sha256=config_entry.sha256_hex,
            size_bytes=config_entry.size_bytes,
            data_base64=base64.b64encode(config_bytes).decode("ascii"),
        )
        layer_descriptors = []
        layers = {}
        for layer in layer_entries:
            descriptor = SandboxDockerImageLayer(
                sha256=layer.sha256_hex,
                size_bytes=layer.size_bytes,
            )
            layer_descriptors.append(descriptor)
            existing = layers.get(layer.sha256_hex)
            if existing is not None and existing.size_bytes != layer.size_bytes:
                raise RuntimeError(
                    f"Docker layer {layer.sha256_hex} has conflicting sizes"
                )
            if existing is None:
                layers[layer.sha256_hex] = DockerImageBuildArtifact(
                    path=layer.path,
                    sha256_hex=layer.sha256_hex,
                    size_bytes=layer.size_bytes,
                    input_format=DOCKER_IMAGE_MANIFEST_INPUT_FORMAT,
                    source_platform=platform,
                )

        descriptor = None
        if image_digest != f"sha256:{config_descriptor.sha256}":
            descriptor = _resolve_oci_image_descriptor(
                entries,
                image_digest,
                config_descriptor,
                layer_descriptors,
            )
        manifest = SandboxDockerImageManifest(
            version=1,
            image_digest=image_digest,
            descriptor=descriptor,
            config=config_descriptor,
            layers=layer_descriptors,
        )
        manifest_bytes = _canonical_model_json(manifest)
        artifact = _write_manifest_artifact(
            workspace,
            "docker-image-manifest.json",
            manifest_bytes,
            DOCKER_IMAGE_MANIFEST_INPUT_FORMAT,
            image_config_user=str(config.get("User") or "").strip(),
            image_init=_derive_auto_image_init(config),
        )
        return PackagedDockerImage(
            artifact=artifact,
            manifest=manifest,
            layers=layers,
            workspace=workspace,
        )
    except Exception:
        if process is not None:
            _cleanup_docker_export_process(process)
            process = None
        shutil.rmtree(workspace, ignore_errors=True)
        raise
    finally:
        if process is not None and process.poll() is not None:
            _cleanup_docker_export_process(process)
        stderr_file.close()


def package_docker_image(
    docker_image: str,
    *,
    platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
    temp_dir: Optional[str] = None,
) -> DockerImageBuildArtifact:
    """Package the legacy flattened-rootfs format.

    This remains public for callers pinned to an older API, while the high-level
    manager now uses reusable Docker layer manifests.
    """
    _ensure_docker_image_source_platform(docker_image, platform)
    container_id = ""
    try:
        container_id = _run_command_output(
            ["docker", "create", f"--platform={platform}", docker_image]
        ).strip()
        if not container_id:
            raise RuntimeError("docker create returned empty container ID")
        config = _inspect_docker_container_config(container_id)
        return _package_docker_container(
            docker_image,
            container_id,
            config,
            platform=platform,
            temp_dir=temp_dir,
        )
    except Exception:
        if container_id:
            _remove_docker_container(container_id)
        raise


def remove_docker_image(image: str) -> None:
    try:
        _run_command(["docker", "image", "rm", image])
    except RuntimeError:
        pass


def upload_image_build_artifact(
    upload: SandboxImageBuildUpload,
    artifact_path: str,
    *,
    timeout: Optional[float] = None,
) -> None:
    artifact_size = os.path.getsize(artifact_path)
    if upload.max_upload_bytes > 0 and artifact_size > upload.max_upload_bytes:
        raise RuntimeError(
            "image artifact exceeds the server upload limit "
            f"({artifact_size} > {upload.max_upload_bytes})"
        )
    method = (upload.method or "PUT").strip().upper()
    attempts = 3 if method == "PUT" else 1
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            _upload_image_build_artifact_once(
                upload,
                artifact_path,
                method=method,
                timeout=timeout,
            )
            return
        except httpx.HTTPError as exc:
            last_error = exc
        except _UploadStatusError as exc:
            last_error = exc
            if exc.status_code not in (408, 429) and exc.status_code < 500:
                raise
        if attempt < attempts:
            time.sleep(attempt * 0.25)
    if last_error is not None:
        raise last_error


def upload_missing_image_build_artifacts(
    uploads: Sequence[SandboxImageBuildUpload],
    artifacts: Dict[str, DockerImageBuildArtifact],
    *,
    label: str,
    timeout: Optional[float] = None,
) -> None:
    requested = []
    seen = set()
    for upload in uploads:
        digest = (upload.sha256 or "").strip().lower()
        if digest not in artifacts:
            raise RuntimeError(f'server requested unknown {label} "{upload.sha256}"')
        if digest in seen:
            raise RuntimeError(f"server requested duplicate {label} {digest}")
        seen.add(digest)
        method = (upload.method or "PUT").strip().upper()
        if method != "PUT":
            raise RuntimeError(
                f'server requested unsupported {label} upload method "{upload.method}"'
            )
        artifact = artifacts[digest]
        if (
            upload.max_upload_bytes > 0
            and artifact.size_bytes > upload.max_upload_bytes
        ):
            raise RuntimeError(
                f"{label} {digest} exceeds the server upload limit "
                f"({artifact.size_bytes} > {upload.max_upload_bytes})"
            )
        requested.append((upload, artifact))
    if not requested:
        return
    with ThreadPoolExecutor(max_workers=min(4, len(requested))) as executor:
        futures = {
            executor.submit(
                upload_image_build_artifact,
                upload,
                artifact.path,
                timeout=timeout,
            ): (upload.sha256 or "").strip().lower()
            for upload, artifact in requested
        }
        for future in as_completed(futures):
            digest = futures[future]
            try:
                future.result()
            except Exception as exc:
                raise RuntimeError(f"upload {label} {digest}: {exc}") from exc


def merge_image_init(
    automatic: Optional[SandboxImageInit],
    explicit: Optional[SandboxImageInit],
) -> Optional[SandboxImageInit]:
    if automatic is None and explicit is None:
        return None
    env = {}
    if automatic is not None and automatic.env:
        env.update(automatic.env)
    if explicit is not None and explicit.env:
        env.update(explicit.env)
    command = (automatic.command or "").strip() if automatic is not None else ""
    args = _normalize_init_args(automatic.args if automatic is not None else None)
    working_dir = (automatic.working_dir or "").strip() if automatic is not None else ""
    if explicit is not None:
        explicit_working_dir = (explicit.working_dir or "").strip()
        if explicit_working_dir:
            working_dir = explicit_working_dir
        explicit_args = _normalize_init_args(explicit.args)
        if explicit_args:
            args = explicit_args
            command = ""
        explicit_command = (explicit.command or "").strip()
        if explicit_command:
            command = explicit_command
            args = []
    if not env and not command and not args and not working_dir:
        return None
    return SandboxImageInit(
        env=env or None,
        command=command or None,
        args=args or None,
        working_dir=working_dir or None,
    )


def make_temp_docker_tag(prefix: str = "hyperbrowser-sdk-build") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


def is_terminal_image_build_status(status: SandboxImageBuildStatus) -> bool:
    return status in TERMINAL_IMAGE_BUILD_STATUSES


class _UploadStatusError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        super().__init__(
            f"image artifact upload failed: {status_code}: {body}".rstrip()
        )


def _upload_image_build_artifact_once(
    upload: SandboxImageBuildUpload,
    artifact_path: str,
    *,
    method: str,
    timeout: Optional[float],
) -> None:
    headers = dict(upload.headers or {})
    headers.setdefault("content-length", str(os.path.getsize(artifact_path)))
    with open(artifact_path, "rb") as artifact:
        response = httpx.request(
            method,
            upload.url,
            content=artifact,
            headers=headers,
            timeout=timeout,
        )
    if response.is_success:
        return
    raise _UploadStatusError(response.status_code, response.text.strip())


def _inspect_docker_image(docker_image: str, platform: str) -> Dict[str, object]:
    output = _run_command_output(
        [
            "docker",
            "image",
            "inspect",
            f"--platform={platform}",
            "--format",
            "{{json .}}",
            docker_image,
        ]
    ).strip()
    try:
        inspection = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("decode Docker image inspection") from exc
    if not isinstance(inspection, dict):
        raise RuntimeError("docker inspect returned an invalid image inspection")
    actual_platform = (
        f"{inspection.get('Os', '')}/{inspection.get('Architecture', '')}".lower()
    )
    if actual_platform != platform.strip().lower():
        raise _unsupported_docker_image_platform_error(
            docker_image,
            actual_platform,
            platform,
        )
    return inspection


def _ensure_docker_image_source_platform(docker_image: str, platform: str) -> None:
    try:
        output = _run_command_output(
            [
                "docker",
                "image",
                "inspect",
                "--format",
                "{{.Os}}/{{.Architecture}}",
                docker_image,
            ]
        )
    except RuntimeError:
        return
    local_platform = output.strip().lower()
    expected_platform = platform.strip().lower()
    if not local_platform or local_platform == expected_platform:
        return
    raise _unsupported_docker_image_platform_error(
        docker_image,
        local_platform,
        platform,
    )


def _unsupported_docker_image_platform_error(
    docker_image: str,
    actual_platform: str,
    expected_platform: str,
) -> RuntimeError:
    return RuntimeError(
        "\n".join(
            [
                "docker image platform is not supported for Hyperbrowser image "
                f"builds: {docker_image} is {actual_platform} "
                f"(expected {expected_platform}).",
                f"Please rebuild the image for {expected_platform} and try again:",
                "  cd <docker-build-context-root>",
                f"  docker buildx build --platform {expected_platform} "
                f"-t {docker_image} -f <path/to/Dockerfile> --load .",
            ]
        )
    )


def _inspect_docker_container_config(container_id: str) -> Dict[str, object]:
    output = _run_command_output(
        [
            "docker",
            "container",
            "inspect",
            "--format",
            "{{json .Config}}",
            container_id,
        ]
    ).strip()
    if not output or output == "null":
        raise RuntimeError("docker inspect returned empty container config")
    try:
        return _require_dict(json.loads(output), "Docker container config")
    except json.JSONDecodeError as exc:
        raise RuntimeError("decode Docker container config") from exc


def _package_docker_container(
    docker_image: str,
    container_id: str,
    config: Dict[str, object],
    *,
    platform: str,
    temp_dir: Optional[str],
) -> DockerImageBuildArtifact:
    tmp = tempfile.NamedTemporaryFile(
        prefix="hb-image-",
        suffix=".tar.gz",
        dir=temp_dir,
        delete=False,
    )
    tmp_path = tmp.name
    hasher = hashlib.sha256()
    writer = _HashingCountingWriter(tmp, hasher)
    stderr_file = tempfile.TemporaryFile()
    process = None
    try:
        process = subprocess.Popen(
            ["docker", "export", container_id],
            stdout=subprocess.PIPE,
            stderr=stderr_file,
        )
        if process.stdout is None:
            raise RuntimeError("docker export did not provide stdout")
        with gzip.GzipFile(fileobj=writer, mode="wb", compresslevel=9) as gzip_file:
            while True:
                chunk = process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                gzip_file.write(chunk)
        return_code = process.wait()
        if return_code != 0:
            stderr_file.seek(0)
            message = stderr_file.read().decode("utf-8", errors="replace").strip()
            if message:
                raise RuntimeError(f"docker export {docker_image} failed: {message}")
            raise RuntimeError(
                f"docker export {docker_image} failed with code {return_code}"
            )
        tmp.flush()
        return DockerImageBuildArtifact(
            path=tmp_path,
            sha256_hex=hasher.hexdigest(),
            size_bytes=writer.total,
            input_format=IMAGE_BUILD_INPUT_FORMAT,
            source_platform=platform,
            image_config_user=str(config.get("User") or "").strip(),
            image_init=_derive_auto_image_init(config),
        )
    except Exception:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise
    finally:
        if process is not None:
            _cleanup_docker_export_process(process)
        tmp.close()
        stderr_file.close()
        _remove_docker_container(container_id)


def _cleanup_docker_export_process(process) -> None:
    if process.stdout is not None:
        process.stdout.close()
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return
    process.wait()


def _derive_auto_image_init(config: Dict[str, object]) -> Optional[SandboxImageInit]:
    env = _derive_auto_image_env(_list_string_config(config.get("Env")))
    args = _derive_auto_startup_args(
        _list_string_config(config.get("Entrypoint")),
        _list_string_config(config.get("Cmd")),
    )
    working_dir = str(config.get("WorkingDir") or "").strip()
    if not env and not args and not working_dir:
        return None
    return SandboxImageInit(
        env=env or None,
        args=args or None,
        working_dir=working_dir or None,
    )


def _derive_auto_image_env(entries: Sequence[str]) -> Dict[str, str]:
    env = {}
    for entry in entries:
        key, sep, value = entry.partition("=")
        if not sep:
            continue
        key = key.strip()
        if (
            not key
            or not _IMAGE_INIT_ENV_KEY_PATTERN.match(key)
            or key in _RESERVED_IMAGE_INIT_ENV_KEYS
        ):
            continue
        env[key] = value
    return env


def _derive_auto_startup_args(
    entrypoint: Sequence[str], cmd: Sequence[str]
) -> List[str]:
    argv = list(entrypoint) + list(cmd) if entrypoint else list(cmd)
    return [arg for arg in argv if arg]


def _normalize_init_args(values: Optional[Sequence[str]]) -> List[str]:
    return [value for value in (values or []) if value]


def _list_string_config(value) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _clean_context_relative_path(value, fallback: str) -> str:
    normalized = str(value or "").strip() or fallback
    normalized = normalized.replace(os.sep, "/")
    if (
        "\\" in normalized
        or any(character in normalized for character in ("\x00", "\r", "\n"))
        or normalized.startswith("/")
    ):
        raise ValueError("Dockerfile path must be relative to the build context")
    if ".." in normalized.split("/"):
        raise ValueError(
            "Dockerfile path must be a relative path inside the build context"
        )
    cleaned = posixpath.normpath(normalized)
    if cleaned in (".", "..") or cleaned.startswith("../"):
        raise ValueError(
            "Dockerfile path must be a relative path inside the build context"
        )
    return cleaned


def _select_dockerignore(context_root: Path, dockerfile_relative: str) -> str:
    dockerfile_ignore = f"{dockerfile_relative}.dockerignore"
    candidate = context_root / dockerfile_ignore
    if candidate.exists():
        if not candidate.is_file():
            raise ValueError(
                f'Dockerfile-specific ignore file "{dockerfile_ignore}" is not '
                "a regular file"
            )
        return dockerfile_ignore
    return ".dockerignore"


def _load_dockerignore(ignore_path: Path) -> Optional[PathSpec]:
    if not ignore_path.exists():
        return None
    try:
        lines = ignore_path.read_text(encoding="utf-8-sig").splitlines()
        return PathSpec.from_lines("gitwildmatch", lines)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"parse .dockerignore: {exc}") from exc


def _analyze_dockerfile_sources(data: bytes) -> Tuple[List[List[str]], str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return [], "dockerfile_parse_failed"
    escape_match = re.search(r"(?im)^\s*#\s*escape\s*=\s*(\S+)", text)
    if escape_match and escape_match.group(1) != "\\":
        return [], "dockerfile_parse_failed"
    syntax_match = re.search(r"(?im)^\s*#\s*syntax\s*=\s*([^\s]+)", text)
    if syntax_match and not _is_official_dockerfile_frontend(syntax_match.group(1)):
        return [], "custom_dockerfile_frontend"
    if "<<" in text:
        return [], "dockerfile_instruction_parse_failed"
    logical_lines = []
    current = ""
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not current and (not stripped or stripped.startswith("#")):
            continue
        current = f"{current}{stripped}"
        if current.endswith("\\"):
            current = current[:-1] + " "
            continue
        logical_lines.append(current.strip())
        current = ""
    if current:
        return [], "dockerfile_parse_failed"

    groups = []
    for line in logical_lines:
        command, separator, body = line.partition(" ")
        if not separator:
            continue
        instruction = command.upper()
        if instruction in ("COPY", "ADD"):
            try:
                flags, values = _parse_copy_add_values(body)
            except (ValueError, json.JSONDecodeError):
                return [], "dockerfile_instruction_parse_failed"
            if instruction == "COPY" and "from" in flags:
                continue
            sources = values[:-1]
            local_sources = []
            for source in sources:
                if "$" in source or "\x00" in source:
                    reason = (
                        "copy_source_requires_expansion"
                        if instruction == "COPY"
                        else "add_source_requires_expansion"
                    )
                    return [], reason
                if instruction == "ADD" and _is_remote_add_source(source):
                    continue
                local_sources.append(source)
            if local_sources:
                groups.append(local_sources)
        elif instruction == "RUN":
            for mount in re.findall(r"--mount=([^\s]+)", body):
                options = {}
                for option in mount.split(","):
                    key, _, value = option.partition("=")
                    options[key.strip()] = value.strip()
                if options.get("type") != "bind" or options.get("from"):
                    continue
                source = options.get("source") or options.get("src") or "."
                if "$" in source:
                    return [], "run_bind_source_requires_expansion"
                groups.append([source])
    return groups, ""


def _parse_copy_add_values(body: str) -> Tuple[Dict[str, str], List[str]]:
    flags = {}
    remaining = body.strip()
    while remaining.startswith("--"):
        token, separator, remaining = remaining.partition(" ")
        if not separator:
            raise ValueError("COPY/ADD is missing source and destination")
        key, has_value, value = token[2:].partition("=")
        flags[key.lower()] = value if has_value else ""
        remaining = remaining.lstrip()
    if remaining.startswith("["):
        values = json.loads(remaining)
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise ValueError("invalid JSON COPY/ADD")
    else:
        values = shlex.split(remaining, posix=True)
    if len(values) < 2:
        raise ValueError("COPY/ADD is missing source or destination")
    return flags, values


def _is_official_dockerfile_frontend(reference: str) -> bool:
    normalized = reference.strip()
    if normalized.startswith("docker-image://"):
        normalized = normalized[len("docker-image://") :]
    normalized = normalized.split("@", 1)[0]
    last_slash = normalized.rfind("/")
    last_colon = normalized.rfind(":")
    if last_colon > last_slash:
        normalized = normalized[:last_colon]
    return normalized in {
        "docker/dockerfile",
        "docker.io/docker/dockerfile",
        "index.docker.io/docker/dockerfile",
        "docker/dockerfile-upstream",
        "docker.io/docker/dockerfile-upstream",
        "index.docker.io/docker/dockerfile-upstream",
    }


def _is_remote_add_source(source: str) -> bool:
    return source.startswith(("http://", "https://", "git://", "ssh://"))


def _deduplicate_source_groups(groups: List[List[str]]) -> List[List[str]]:
    result = []
    seen = set()
    for group in groups:
        normalized = tuple(sorted(_normalize_context_source(item) for item in group))
        if normalized not in seen:
            seen.add(normalized)
            result.append(list(normalized))
    return result


def _normalize_context_source(source: str) -> str:
    if "\x00" in source:
        raise ValueError("Dockerfile source path contains a NUL byte")
    normalized = str(source).strip().replace("\\", "/")
    if normalized in ("", ".", "/"):
        return "."
    normalized = posixpath.normpath("/" + normalized).lstrip("/")
    return normalized or "."


def _collect_context_entries(
    context_root: Path,
    sources: Sequence[str],
    *,
    ignore_spec: Optional[PathSpec],
    required: bool,
):
    entries = set()
    for raw_source in sources:
        source = _normalize_context_source(raw_source)
        if source == ".":
            matches = [context_root]
        elif glob.has_magic(source):
            matches = [
                Path(path)
                for path in glob.glob(str(context_root / source), recursive=True)
            ]
        else:
            matches = [context_root / source]
        existing_matches = [
            path for path in matches if path.exists() or path.is_symlink()
        ]
        if required and not existing_matches:
            raise FileNotFoundError(
                f'Docker build context source not found: "{source}"'
            )
        for match in existing_matches:
            resolved_parent = (
                context_root
                if match == context_root
                else match.parent.resolve(strict=True)
            )
            if not _path_is_within(context_root, resolved_parent):
                raise ValueError(
                    f'Docker build context source escapes context: "{source}"'
                )
            _collect_context_path(context_root, match, entries, ignore_spec)
    return entries


def _collect_context_path(
    context_root: Path,
    path: Path,
    entries,
    ignore_spec: Optional[PathSpec],
) -> None:
    relative = path.relative_to(context_root).as_posix()
    if relative != "." and not _is_ignored(relative, path.is_dir(), ignore_spec):
        entries.add(relative)
    if path.is_symlink() or not path.is_dir():
        return
    for root, directories, files in os.walk(str(path), followlinks=False):
        root_path = Path(root)
        for name in sorted(directories + files):
            child = root_path / name
            child_relative = child.relative_to(context_root).as_posix()
            if _is_ignored(child_relative, child.is_dir(), ignore_spec):
                continue
            entries.add(child_relative)


def _is_ignored(relative: str, is_directory: bool, spec: Optional[PathSpec]) -> bool:
    if spec is None:
        return False
    candidate = f"{relative}/" if is_directory else relative
    return spec.match_file(candidate)


def _remove_subsumed_entry_groups(groups):
    result = []
    for index, entries in enumerate(groups):
        if any(
            index != candidate_index
            and entries <= candidate
            and (entries != candidate or index > candidate_index)
            for candidate_index, candidate in enumerate(groups)
        ):
            continue
        result.append(entries)
    return result


def _package_context_bundle(
    context_root: Path,
    entries: Sequence[str],
    workspace: str,
    index: int,
) -> Tuple[DockerImageBuildArtifact, SandboxBuildContextBundle]:
    bundle_path = os.path.join(workspace, f"bundle-{index:04d}.tar.gz")
    hasher = hashlib.sha256()
    uncompressed_size = 0
    entry_count = 0
    with open(bundle_path, "wb") as destination:
        writer = _HashingCountingWriter(destination, hasher)
        with gzip.GzipFile(
            filename="",
            fileobj=writer,
            mode="wb",
            compresslevel=1,
            mtime=0,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed,
                mode="w",
                format=tarfile.PAX_FORMAT,
            ) as archive:
                for relative in entries:
                    _validate_archive_relative_path(relative)
                    absolute = context_root / relative
                    info = archive.gettarinfo(str(absolute), arcname=relative)
                    if not (info.isfile() or info.isdir() or info.issym()):
                        continue
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.pax_headers = {}
                    if info.isdir() and not info.name.endswith("/"):
                        info.name += "/"
                    if info.issym() and not info.linkname:
                        raise ValueError(
                            f'build context symlink "{relative}" has an invalid target'
                        )
                    if info.isfile():
                        with open(absolute, "rb") as source:
                            archive.addfile(info, source)
                        uncompressed_size += info.size
                    else:
                        archive.addfile(info)
                    entry_count += 1
    size_bytes = os.path.getsize(bundle_path)
    sha256_hex = hasher.hexdigest()
    artifact = DockerImageBuildArtifact(
        path=bundle_path,
        sha256_hex=sha256_hex,
        size_bytes=size_bytes,
        input_format=CONTEXT_MANIFEST_INPUT_FORMAT,
    )
    descriptor = SandboxBuildContextBundle(
        sha256=sha256_hex,
        size_bytes=size_bytes,
        uncompressed_size_bytes=uncompressed_size,
        entry_count=entry_count,
    )
    return artifact, descriptor


def _normalize_docker_save_entry_name(raw: str) -> str:
    if (
        not raw
        or "\\" in raw
        or any(character in raw for character in ("\x00", "\r", "\n"))
        or raw.startswith("/")
    ):
        raise RuntimeError("docker image save contains an unsafe entry path")
    normalized = posixpath.normpath(raw)
    if normalized in (".", "..") or normalized.startswith("../") or normalized != raw:
        raise RuntimeError("docker image save contains an unsafe entry path")
    return normalized


def _store_streamed_entry(
    source,
    destination: str,
    expected_size: int,
    name: str,
) -> _StoredDockerSaveEntry:
    hasher = hashlib.sha256()
    written = 0
    with open(destination, "xb") as output:
        while written < expected_size:
            chunk = source.read(min(1024 * 1024, expected_size - written))
            if not chunk:
                break
            output.write(chunk)
            hasher.update(chunk)
            written += len(chunk)
    if written != expected_size:
        raise RuntimeError(f'docker image save entry "{name}" has truncated content')
    return _StoredDockerSaveEntry(
        path=destination,
        sha256_hex=hasher.hexdigest(),
        size_bytes=written,
    )


def _resolve_docker_save_manifest(entries):
    manifest_entry = entries.get("manifest.json")
    if (
        manifest_entry is None
        or manifest_entry.size_bytes <= 0
        or manifest_entry.size_bytes > _MAX_DOCKER_SAVE_METADATA_BYTES
    ):
        raise RuntimeError("docker image save manifest.json is missing or too large")
    try:
        manifest = json.loads(Path(manifest_entry.path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("docker image save manifest.json is invalid") from exc
    if not isinstance(manifest, list) or len(manifest) != 1:
        raise RuntimeError("docker image save must contain exactly one manifest entry")
    item = _require_dict(manifest[0], "Docker save manifest entry")
    config_name = _normalize_docker_save_entry_name(str(item.get("Config") or ""))
    config_entry = entries.get(config_name)
    if (
        config_entry is None
        or config_entry.size_bytes <= 0
        or config_entry.size_bytes > _MAX_DOCKER_SAVE_METADATA_BYTES
    ):
        raise RuntimeError("docker image save config is missing or too large")
    raw_layers = item.get("Layers")
    if not isinstance(raw_layers, list) or len(raw_layers) > _MAX_DOCKER_IMAGE_LAYERS:
        raise RuntimeError("docker image save has too many layers")
    layers = []
    for raw_layer in raw_layers:
        layer_name = _normalize_docker_save_entry_name(str(raw_layer))
        layer = entries.get(layer_name)
        if layer is None or layer.size_bytes <= 0:
            raise RuntimeError(f'docker image save layer "{layer_name}" is missing')
        layers.append(layer)
    return config_entry, layers


def _resolve_oci_image_descriptor(
    entries,
    image_digest: str,
    config: SandboxDockerImageConfig,
    layers: Sequence[SandboxDockerImageLayer],
) -> SandboxDockerImageConfig:
    digest_hex = image_digest[len("sha256:") :]
    entry = entries.get(f"blobs/sha256/{digest_hex}")
    if (
        entry is None
        or entry.sha256_hex != digest_hex
        or entry.size_bytes <= 0
        or entry.size_bytes > _MAX_DOCKER_SAVE_METADATA_BYTES
    ):
        raise RuntimeError(
            "docker image save is missing its inspected OCI image manifest"
        )
    data = Path(entry.path).read_bytes()
    descriptor = _require_json_object(data, "OCI image manifest")
    if descriptor.get("schemaVersion") != 2:
        raise RuntimeError(
            "inspected Docker image descriptor is not a valid OCI image manifest"
        )
    descriptor_config = _require_dict(descriptor.get("config"), "OCI config")
    if (
        descriptor_config.get("digest") != f"sha256:{config.sha256}"
        or descriptor_config.get("size") != config.size_bytes
    ):
        raise RuntimeError(
            "OCI image manifest config does not match Docker save config"
        )
    descriptor_layers = descriptor.get("layers")
    if not isinstance(descriptor_layers, list) or len(descriptor_layers) != len(layers):
        raise RuntimeError(
            "OCI image manifest layer count does not match Docker save manifest"
        )
    for index, (raw_layer, layer) in enumerate(zip(descriptor_layers, layers)):
        item = _require_dict(raw_layer, f"OCI layer {index}")
        if (
            item.get("digest") != f"sha256:{layer.sha256}"
            or item.get("size") != layer.size_bytes
        ):
            raise RuntimeError(
                f"OCI image manifest layer {index} does not match Docker save manifest"
            )
    return SandboxDockerImageConfig(
        sha256=entry.sha256_hex,
        size_bytes=entry.size_bytes,
        data_base64=base64.b64encode(data).decode("ascii"),
    )


def _canonical_model_json(model) -> bytes:
    payload = model.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_manifest_artifact(
    workspace: str,
    filename: str,
    data: bytes,
    input_format: SandboxImageBuildInputFormat,
    *,
    image_config_user: str = "",
    image_init: Optional[SandboxImageInit] = None,
) -> DockerImageBuildArtifact:
    path = os.path.join(workspace, filename)
    with open(path, "xb") as output:
        output.write(data)
    return DockerImageBuildArtifact(
        path=path,
        sha256_hex=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        input_format=input_format,
        image_config_user=image_config_user,
        image_init=image_init,
    )


def _validate_archive_relative_path(relative: str) -> None:
    if (
        not relative
        or relative.startswith("/")
        or "\x00" in relative
        or posixpath.normpath(relative) != relative
        or relative == ".."
        or relative.startswith("../")
    ):
        raise ValueError(f'invalid build context path "{relative}"')


def _path_is_within(parent: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def _normalize_sha256_digest(value) -> str:
    digest = str(value or "").strip().lower()
    if not digest.startswith("sha256:") or not _SHA256_PATTERN.fullmatch(digest[7:]):
        raise RuntimeError(
            "docker inspect returned an invalid linux/amd64 image digest"
        )
    return digest


def _require_dict(value, label: str) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _require_json_object(data: bytes, label: str) -> Dict[str, object]:
    try:
        return _require_dict(json.loads(data.decode("utf-8")), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} is not valid JSON") from exc


def _remove_docker_container(container_id: str) -> None:
    try:
        _run_command(["docker", "rm", "-f", container_id])
    except RuntimeError:
        pass


def _run_command(args: Sequence[str]) -> None:
    _run_command_result(args)


def _run_command_output(args: Sequence[str]) -> str:
    return _run_command_result(args).stdout


def _run_command_result(args: Sequence[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(
        list(args),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return result
    message = result.stderr.strip()
    if message:
        raise RuntimeError(f"{' '.join(args)}: {message}")
    raise RuntimeError(f"{' '.join(args)} failed with code {result.returncode}")
