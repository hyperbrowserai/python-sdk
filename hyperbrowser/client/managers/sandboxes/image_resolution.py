"""Shared identity and validation for opt-in image resolution."""

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Literal, Optional, Union

from ....exceptions import HyperbrowserError
from ....models.sandbox import SandboxImageBuild, SandboxImageInit
from ....types import SandboxImageInit as SandboxImageInitDict
from ..._request import coerce_request


def image_build_name(
    *,
    source: Literal["dockerfile", "prebuilt"],
    fingerprint: str,
    name_prefix: str = "hb",
    platform: str = "linux/amd64",
    image_init: Optional[Union[SandboxImageInitDict, SandboxImageInit]] = None,
    image_config_user: Optional[str] = None,
) -> str:
    """Name an immutable input identity without packaging or uploading it.

    Fingerprints identify effective Dockerfile contexts or platform-specific
    Docker image digests. Builder resources and wait policies do not change the
    image contents and are excluded. Mutable external inputs (base tags, network
    downloads) require an explicit force_build to request another build.
    """
    platform = platform.strip().lower()
    if not re.fullmatch(r"[a-z0-9]+/[a-z0-9]+(?:/[a-z0-9]+)?", platform):
        raise ValueError("platform must be an OCI platform such as 'linux/amd64'")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,21}", name_prefix):
        raise ValueError("image_name_prefix must be 1-21 letters, digits, '_' or '-'")
    if source == "prebuilt":
        fingerprint = fingerprint.lower()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
            raise ValueError("expected_image_digest must be a sha256: Docker digest")
        payload = "docker_image\0{}\0platform\0{}".format(fingerprint, platform)
    elif source == "dockerfile":
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError(
                "expected_context_fingerprint must be a SHA-256 hex digest"
            )
        payload = "dockerfile-context-v3\0{}\0platform\0{}".format(
            fingerprint, platform
        )
    else:
        raise ValueError("source must be 'dockerfile' or 'prebuilt'")
    options = {}
    if image_init is not None:
        normalized = coerce_request(image_init, SandboxImageInit, name="image_init")
        initialization = normalized.model_dump(by_alias=True, exclude_none=True)
        if initialization:
            options["imageInit"] = initialization
    if image_config_user is not None:
        options["imageConfigUser"] = image_config_user.strip()
    if options:
        payload += "\0options\0" + json.dumps(
            options, sort_keys=True, separators=(",", ":")
        )
    digest = hashlib.blake2b(payload.encode(), digest_size=8).hexdigest()
    name = "{}__{}__{}__{}".format(
        name_prefix, source, digest, platform.replace("/", "-")
    )
    if len(name) > 64:
        raise ValueError(
            "image_name_prefix and platform produce a name longer than 64 characters"
        )
    return name


def matching_image_build(
    error: HyperbrowserError, image_name: str, input_format: str
) -> Optional[SandboxImageBuild]:
    if error.status_code != 409 or error.code != "image_build_in_progress":
        return None
    if not isinstance(error.details, Mapping):
        return None
    data = error.details.get("build")
    if not isinstance(data, Mapping):
        return None
    metadata = data.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("inputFormat") != input_format:
        return None
    if metadata.get("sourcePlatform", "linux/amd64") != "linux/amd64":
        return None
    try:
        build = SandboxImageBuild(**dict(data))
    except (TypeError, ValueError):
        return None
    if not build.id or build.image_name != image_name:
        return None
    return build


def completed_image_id(build: SandboxImageBuild) -> Optional[str]:
    if build.status != "completed":
        return None
    if not build.image_id:
        raise RuntimeError("Completed image build did not return an image ID")
    return build.image_id
