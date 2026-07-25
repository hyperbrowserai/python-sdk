from typing import Dict, List, Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict


SandboxStatus: TypeAlias = Literal["active", "closed", "error"]
SandboxRegion: TypeAlias = Literal[
    "us-central",
    "asia-south",
    "us-dev",
    "europe-west",
    "us-west",
    "us-east",
    "us",
]
SandboxProcessStatus: TypeAlias = Literal[
    "queued",
    "running",
    "exited",
    "failed",
    "killed",
    "timed_out",
]
SandboxSnapshotStatus: TypeAlias = Literal["creating", "created", "failed"]
SandboxFileEncoding: TypeAlias = Literal["utf8", "base64"]
SandboxFileReadFormat: TypeAlias = Literal["text", "bytes", "blob", "stream"]
SandboxFileWatchRoute: TypeAlias = Literal["ws", "stream"]
SandboxVolumeMountType: TypeAlias = Literal["rw", "ro"]
SandboxImageBuildInputFormat: TypeAlias = Literal["rootfs_export_tar_gz"]
SandboxFileWriteData: TypeAlias = Union[str, bytes]


class SandboxExposeParams(TypedDict, total=False):
    """Parameters for exposing a port from a sandbox."""

    port: Required[int]
    auth: Optional[bool]


class SandboxVolumeMount(TypedDict, total=False):
    """A persistent volume mounted into a sandbox."""

    id: Required[str]
    type: Optional[SandboxVolumeMountType]
    shared: Optional[bool]


class SandboxNetworkPolicy(TypedDict, total=False):
    """Outbound network policy for a sandbox."""

    allow_internet_access: Optional[bool]
    allow_out: List[str]
    deny_out: List[str]


class _CreateSandboxCommon(TypedDict, total=False):
    """Fields shared by image- and snapshot-based sandbox launches."""

    region: Optional[SandboxRegion]
    enable_recording: Optional[bool]
    exposed_ports: Optional[List[SandboxExposeParams]]
    mounts: Optional[Dict[str, SandboxVolumeMount]]
    timeout_minutes: Optional[int]
    allow_internet_access: Optional[bool]
    allow_out: Optional[List[str]]
    deny_out: Optional[List[str]]


class CreateSandboxFromSnapshotParams(_CreateSandboxCommon, total=False):
    """Parameters for creating a sandbox from a memory snapshot."""

    snapshot_name: Required[str]
    snapshot_id: Optional[str]


class CreateSandboxFromImageParams(_CreateSandboxCommon, total=False):
    """Parameters for creating a sandbox from an image."""

    image_name: Required[str]
    image_id: Optional[str]
    cpu: Optional[int]
    memory_mib: Optional[int]
    disk_mib: Optional[int]


CreateSandboxParams: TypeAlias = Union[
    CreateSandboxFromSnapshotParams,
    CreateSandboxFromImageParams,
]
StartSandboxFromSnapshotParams: TypeAlias = CreateSandboxFromSnapshotParams


class SandboxListParams(TypedDict, total=False):
    """Filters and pagination for listing sandboxes."""

    status: Optional[SandboxStatus]
    page: int
    limit: int
    start: Optional[int]
    end: Optional[int]
    search: Optional[str]


class SandboxImageInit(TypedDict, total=False):
    """Startup environment and command stored in a sandbox image."""

    env: Optional[Dict[str, str]]
    command: Optional[str]
    args: Optional[List[str]]


class SandboxImageListParams(TypedDict, total=False):
    """Filters and pagination for listing sandbox images."""

    page: Optional[int]
    limit: Optional[int]
    search: Optional[str]
    sources: Optional[List[str]]


class SandboxSnapshotListParams(TypedDict, total=False):
    """Filters and pagination for listing sandbox snapshots."""

    status: Optional[Union[SandboxSnapshotStatus, List[SandboxSnapshotStatus]]]
    limit: Optional[int]
    image_name: Optional[str]
    search: Optional[str]
    page: Optional[int]


class SandboxMemorySnapshotParams(TypedDict, total=False):
    """Parameters for creating a sandbox memory snapshot."""

    snapshot_name: Optional[str]


class CreateSandboxImageBuildParams(TypedDict, total=False):
    """Metadata for starting an uploaded sandbox image build."""

    image_name: Required[str]
    input_sha256: Required[str]
    input_size_bytes: Required[int]
    input_format: SandboxImageBuildInputFormat
    source_platform: str
    image_config_user: Optional[str]
    image_init: Optional[SandboxImageInit]


class CompleteSandboxImageBuildParams(TypedDict, total=False):
    """Metadata used to complete a sandbox image upload."""

    input_sha256: Required[str]
    input_size_bytes: Required[int]
    input_format: SandboxImageBuildInputFormat


class SandboxExecParams(TypedDict, total=False):
    """Parameters for executing a command in a sandbox."""

    command: Required[str]
    args: Optional[List[str]]
    cwd: Optional[str]
    env: Optional[Dict[str, str]]
    timeout_ms: Optional[int]
    timeout_sec: Optional[int]
    run_as: Optional[str]
    use_shell: Optional[bool]


class SandboxProcessListParams(TypedDict, total=False):
    """Filters and pagination for sandbox processes."""

    status: Optional[Union[SandboxProcessStatus, List[SandboxProcessStatus]]]
    limit: Optional[int]
    cursor: Optional[Union[str, int]]
    created_after: Optional[int]
    created_before: Optional[int]


class SandboxProcessWaitParams(TypedDict, total=False):
    """Timeout options for waiting on a sandbox process."""

    timeout_ms: Optional[int]
    timeout_sec: Optional[int]


class SandboxProcessStdinParams(TypedDict, total=False):
    """Input to write to a running sandbox process."""

    data: Optional[Union[str, bytes]]
    encoding: Optional[SandboxFileEncoding]
    eof: Optional[bool]


class SandboxFileListOptions(TypedDict, total=False):
    """Options for listing a sandbox directory."""

    depth: Optional[int]


class SandboxFileListParams(TypedDict, total=False):
    """Parameters for listing a sandbox directory."""

    path: Required[str]
    depth: Optional[int]


class SandboxFileReadOptions(TypedDict, total=False):
    """Offset, length, and format options for reading a file."""

    offset: Optional[int]
    length: Optional[int]
    format: Optional[SandboxFileReadFormat]


class SandboxFileReadParams(TypedDict, total=False):
    """Parameters for reading a file from a sandbox."""

    path: Required[str]
    offset: Optional[int]
    length: Optional[int]
    encoding: Optional[SandboxFileEncoding]


class SandboxFileWriteEntry(TypedDict, total=False):
    """One file in a sandbox batch-write request."""

    path: Required[str]
    data: Required[SandboxFileWriteData]
    encoding: Optional[SandboxFileEncoding]
    append: Optional[bool]
    mode: Optional[str]


class SandboxFileTextWriteOptions(TypedDict, total=False):
    """Options for writing text to a sandbox file."""

    append: Optional[bool]
    mode: Optional[str]


class SandboxFileBytesWriteOptions(TypedDict, total=False):
    """Options for writing bytes to a sandbox file."""

    append: Optional[bool]
    mode: Optional[str]


class SandboxFileWriteTextParams(TypedDict, total=False):
    """Parameters for writing text to a sandbox file."""

    path: Required[str]
    data: Required[str]
    append: Optional[bool]
    mode: Optional[str]


class SandboxFileWriteBytesParams(TypedDict, total=False):
    """Parameters for writing bytes to a sandbox file."""

    path: Required[str]
    data: Required[bytes]
    append: Optional[bool]
    mode: Optional[str]


class SandboxFileUploadParams(TypedDict):
    """A file path and payload to upload to a sandbox."""

    path: str
    data: Union[bytes, str]


class SandboxFileRemoveOptions(TypedDict, total=False):
    """Options for deleting a sandbox file or directory."""

    recursive: Optional[bool]


class SandboxFileDeleteParams(TypedDict, total=False):
    """Parameters for deleting a sandbox file or directory."""

    path: Required[str]
    recursive: Optional[bool]


class SandboxFileMakeDirOptions(TypedDict, total=False):
    """Options for creating a directory in a sandbox."""

    parents: Optional[bool]
    mode: Optional[str]


class SandboxFileMkdirParams(TypedDict, total=False):
    """Parameters for creating a directory in a sandbox."""

    path: Required[str]
    parents: Optional[bool]
    mode: Optional[str]


class SandboxFileMoveParams(TypedDict, total=False):
    """Parameters for moving a sandbox file or directory."""

    source: Required[str]
    destination: Required[str]
    overwrite: Optional[bool]


class SandboxFileCopyParams(TypedDict, total=False):
    """Parameters for copying a sandbox file or directory."""

    source: Required[str]
    destination: Required[str]
    recursive: Optional[bool]
    overwrite: Optional[bool]


class SandboxFileChmodParams(TypedDict, total=False):
    """Parameters for changing sandbox file permissions."""

    path: Required[str]
    mode: Required[str]
    recursive: Optional[bool]


class SandboxFileChownParams(TypedDict, total=False):
    """Parameters for changing sandbox file ownership."""

    path: Required[str]
    uid: Optional[int]
    gid: Optional[int]
    recursive: Optional[bool]


class SandboxFileWatchParams(TypedDict, total=False):
    """Parameters for watching a sandbox file or directory."""

    path: Required[str]
    recursive: Optional[bool]


class SandboxFileWatchEventsParams(TypedDict, total=False):
    """Cursor and transport options for watched file events."""

    cursor: Optional[int]
    route: Optional[SandboxFileWatchRoute]


class SandboxPresignFileParams(TypedDict, total=False):
    """Parameters for creating a presigned sandbox file URL."""

    path: Required[str]
    expires_in_seconds: Optional[int]
    one_time: Optional[bool]


class SandboxTerminalCreateParams(TypedDict, total=False):
    """Parameters for creating a terminal in a sandbox."""

    command: Required[str]
    args: Optional[List[str]]
    cwd: Optional[str]
    env: Optional[Dict[str, str]]
    use_shell: Optional[bool]
    rows: Optional[int]
    cols: Optional[int]
    timeout_ms: Optional[int]


class SandboxTerminalWaitParams(TypedDict, total=False):
    """Options for waiting on a sandbox terminal."""

    timeout_ms: Optional[int]
    include_output: Optional[bool]


class SandboxTerminalKillParams(TypedDict, total=False):
    """Options for terminating a sandbox terminal."""

    signal: Optional[str]
    timeout_ms: Optional[int]


__all__ = [
    "CompleteSandboxImageBuildParams",
    "CreateSandboxFromImageParams",
    "CreateSandboxFromSnapshotParams",
    "CreateSandboxImageBuildParams",
    "CreateSandboxParams",
    "SandboxExecParams",
    "SandboxExposeParams",
    "SandboxFileBytesWriteOptions",
    "SandboxFileChmodParams",
    "SandboxFileChownParams",
    "SandboxFileCopyParams",
    "SandboxFileDeleteParams",
    "SandboxFileEncoding",
    "SandboxFileListOptions",
    "SandboxFileListParams",
    "SandboxFileMakeDirOptions",
    "SandboxFileMkdirParams",
    "SandboxFileMoveParams",
    "SandboxFileReadFormat",
    "SandboxFileReadOptions",
    "SandboxFileReadParams",
    "SandboxFileRemoveOptions",
    "SandboxFileTextWriteOptions",
    "SandboxFileUploadParams",
    "SandboxFileWatchEventsParams",
    "SandboxFileWatchParams",
    "SandboxFileWatchRoute",
    "SandboxFileWriteBytesParams",
    "SandboxFileWriteData",
    "SandboxFileWriteEntry",
    "SandboxFileWriteTextParams",
    "SandboxImageBuildInputFormat",
    "SandboxImageInit",
    "SandboxImageListParams",
    "SandboxListParams",
    "SandboxMemorySnapshotParams",
    "SandboxNetworkPolicy",
    "SandboxPresignFileParams",
    "SandboxProcessListParams",
    "SandboxProcessStatus",
    "SandboxProcessStdinParams",
    "SandboxProcessWaitParams",
    "SandboxRegion",
    "SandboxSnapshotListParams",
    "SandboxSnapshotStatus",
    "SandboxStatus",
    "SandboxTerminalCreateParams",
    "SandboxTerminalKillParams",
    "SandboxTerminalWaitParams",
    "SandboxVolumeMount",
    "SandboxVolumeMountType",
    "StartSandboxFromSnapshotParams",
]
