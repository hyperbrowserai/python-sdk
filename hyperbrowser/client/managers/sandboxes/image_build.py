import gzip
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence

import httpx

from ....models.sandbox import (
    SandboxImageBuildInputFormat,
    SandboxImageBuildStatus,
    SandboxImageBuildUpload,
    SandboxImageInit,
)

IMAGE_BUILD_INPUT_FORMAT: SandboxImageBuildInputFormat = "rootfs_export_tar_gz"
IMAGE_BUILD_SOURCE_PLATFORM = "linux/amd64"
TERMINAL_IMAGE_BUILD_STATUSES: FrozenSet[SandboxImageBuildStatus] = frozenset(
    {"completed", "failed", "canceled", "cancelled"}
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


@dataclass
class DockerImageBuildArtifact:
    path: str
    sha256_hex: str
    size_bytes: int
    input_format: SandboxImageBuildInputFormat
    source_platform: str
    image_config_user: str
    image_init: Optional[SandboxImageInit]

    def cleanup(self) -> None:
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


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


def package_docker_image(
    docker_image: str,
    *,
    platform: str = IMAGE_BUILD_SOURCE_PLATFORM,
    temp_dir: Optional[str] = None,
) -> DockerImageBuildArtifact:
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
    method = upload.method.strip() if upload.method else "PUT"
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
    body = response.text.strip()
    if body:
        raise RuntimeError(
            f"image artifact upload failed: {response.status_code}: {body}"
        )
    raise RuntimeError(f"image artifact upload failed: {response.status_code}")


def make_temp_docker_tag(prefix: str = "hyperbrowser-sdk-build") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


def is_terminal_image_build_status(status: SandboxImageBuildStatus) -> bool:
    return status in TERMINAL_IMAGE_BUILD_STATUSES


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

    raise RuntimeError(
        "\n".join(
            [
                "docker image platform is not supported for Hyperbrowser image "
                f"builds: {docker_image} is {local_platform} (expected {platform}).",
                f"Please rebuild the image for {platform} and try again:",
                "  cd <docker-build-context-root>",
                f"  docker buildx build --platform {platform} -t {docker_image} "
                "-f <path/to/Dockerfile> --load .",
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
    return json.loads(output)


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
    if not env and not args:
        return None
    return SandboxImageInit(env=env or None, args=args or None)


def _derive_auto_image_env(entries: Sequence[str]) -> Dict[str, str]:
    env = {}
    for entry in entries:
        key, sep, value = entry.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        if not _IMAGE_INIT_ENV_KEY_PATTERN.match(key):
            continue
        if key in _RESERVED_IMAGE_INIT_ENV_KEYS:
            continue
        env[key] = value
    return env


def _derive_auto_startup_args(
    entrypoint: Sequence[str], cmd: Sequence[str]
) -> List[str]:
    argv = list(entrypoint) + list(cmd) if entrypoint else list(cmd)
    return [arg for arg in argv if arg]


def _list_string_config(value) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


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
