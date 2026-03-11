from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .session import SessionLaunchState, SessionStatus

SandboxStatus = SessionStatus
SandboxRegion = Literal[
    "us-central",
    "asia-south",
    "us-dev",
    "europe-west",
    "us-west",
    "us-east",
    "us",
]
SandboxProcessStatus = Literal[
    "queued",
    "running",
    "exited",
    "failed",
    "killed",
    "timed_out",
]
SandboxFileType = Literal["file", "dir"]
SandboxFileEncoding = Literal["utf8", "base64"]
SandboxFileReadFormat = Literal["text", "bytes", "blob", "stream"]
SandboxFileWatchRoute = Literal["ws", "stream"]
SandboxFileSystemEventType = Literal["chmod", "create", "remove", "rename", "write"]


def _parse_optional_datetime(value):
    if value in (None, ""):
        return None
    return value


def _parse_optional_int(value):
    if value is None or isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, str):
        return int(value)
    return value


def _parse_optional_datetime_from_millis(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    return value


class SandboxBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SandboxRuntimeTarget(SandboxBaseModel):
    transport: Literal["regional_proxy"]
    host: str
    base_url: str = Field(alias="baseUrl")


class Sandbox(SandboxBaseModel):
    id: str
    team_id: str = Field(alias="teamId")
    status: SandboxStatus
    end_time: Optional[int] = Field(default=None, alias="endTime")
    start_time: Optional[int] = Field(default=None, alias="startTime")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    close_reason: Optional[str] = Field(default=None, alias="closeReason")
    data_consumed: Optional[int] = Field(default=None, alias="dataConsumed")
    proxy_data_consumed: Optional[int] = Field(
        default=None, alias="proxyDataConsumed"
    )
    usage_type: Optional[str] = Field(default=None, alias="usageType")
    job_id: Optional[str] = Field(default=None, alias="jobId")
    launch_state: Optional[SessionLaunchState] = Field(
        default=None, alias="launchState"
    )
    credits_used: Optional[float] = Field(default=None, alias="creditsUsed")
    region: SandboxRegion
    session_url: str = Field(alias="sessionUrl")
    duration: int
    proxy_bytes_used: Optional[int] = Field(default=None, alias="proxyBytesUsed")
    runtime: SandboxRuntimeTarget

    @field_validator(
        "end_time",
        "start_time",
        "data_consumed",
        "proxy_data_consumed",
        "proxy_bytes_used",
        mode="before",
    )
    @classmethod
    def parse_optional_int_fields(cls, value):
        return _parse_optional_int(value)


class SandboxDetail(Sandbox):
    token: Optional[str] = None
    token_expires_at: Optional[datetime] = Field(default=None, alias="tokenExpiresAt")

    @field_validator("token_expires_at", mode="before")
    @classmethod
    def parse_token_expires_at(cls, value):
        return _parse_optional_datetime(value)


class SandboxRuntimeSession(SandboxBaseModel):
    sandbox_id: str = Field(alias="sandboxId")
    status: SandboxStatus
    region: SandboxRegion
    token: str
    token_expires_at: Optional[datetime] = Field(default=None, alias="tokenExpiresAt")
    runtime: SandboxRuntimeTarget

    @field_validator("token_expires_at", mode="before")
    @classmethod
    def parse_token_expires_at(cls, value):
        return _parse_optional_datetime(value)


class CreateSandboxParams(SandboxBaseModel):
    sandbox_name: Optional[str] = Field(default=None, alias="sandboxName")
    snapshot_name: Optional[str] = Field(default=None, alias="snapshotName")
    snapshot_id: Optional[str] = Field(default=None, alias="snapshotId")
    image_name: Optional[str] = Field(default=None, alias="imageName")
    image_id: Optional[str] = Field(default=None, alias="imageId")
    region: Optional[SandboxRegion] = None
    enable_recording: Optional[bool] = Field(default=None, alias="enableRecording")
    timeout_minutes: Optional[int] = Field(default=None, alias="timeoutMinutes")

    @model_validator(mode="after")
    def validate_launch_source(self):
        source_count = sum(
            bool(value)
            for value in [self.sandbox_name, self.snapshot_name, self.image_name]
        )
        if source_count != 1:
            raise ValueError(
                "Provide exactly one start source: sandbox_name, snapshot_name, or image_name"
            )
        if self.snapshot_id and not self.snapshot_name:
            raise ValueError("snapshot_id requires snapshot_name")
        if self.image_id and not self.image_name:
            raise ValueError("image_id requires image_name")
        return self


class StartSandboxFromSnapshotParams(CreateSandboxParams):
    pass


class SandboxListParams(SandboxBaseModel):
    status: Optional[SandboxStatus] = None
    page: Optional[int] = None
    limit: Optional[int] = None
    search: Optional[str] = None


class SandboxListResponse(SandboxBaseModel):
    sandboxes: List[Sandbox]
    total_count: int = Field(alias="totalCount")
    page: int
    per_page: int = Field(alias="perPage")


class SandboxMemorySnapshotParams(SandboxBaseModel):
    snapshot_name: Optional[str] = Field(default=None, alias="snapshotName")


class SandboxMemorySnapshotResult(SandboxBaseModel):
    snapshot_name: str = Field(alias="snapshotName")
    snapshot_id: str = Field(alias="snapshotId")
    namespace: str
    status: str
    image_name: str = Field(alias="imageName")
    image_id: str = Field(alias="imageId")
    image_namespace: str = Field(alias="imageNamespace")


class SandboxExposeParams(SandboxBaseModel):
    port: int
    auth: Optional[bool] = None


class SandboxExposeResult(SandboxBaseModel):
    port: int
    auth: bool
    url: str


class SandboxExecParams(SandboxBaseModel):
    command: str
    args: Optional[List[str]] = None
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")
    timeout_sec: Optional[int] = Field(default=None, alias="timeoutSec")
    use_shell: Optional[bool] = Field(default=None, alias="useShell")


class SandboxProcessSummary(SandboxBaseModel):
    id: str
    status: SandboxProcessStatus
    command: str
    args: Optional[List[str]] = None
    cwd: str
    pid: Optional[int] = None
    exit_code: Optional[int] = Field(default=None, alias="exit_code")
    started_at: int = Field(alias="started_at")
    completed_at: Optional[int] = Field(default=None, alias="completed_at")


class SandboxProcessResult(SandboxBaseModel):
    id: str
    status: SandboxProcessStatus
    exit_code: Optional[int] = Field(default=None, alias="exit_code")
    stdout: str
    stderr: str
    started_at: int = Field(alias="started_at")
    completed_at: Optional[int] = Field(default=None, alias="completed_at")
    error: Optional[str] = None


class SandboxProcessListParams(SandboxBaseModel):
    status: Optional[Union[SandboxProcessStatus, List[SandboxProcessStatus]]] = None
    limit: Optional[int] = None
    cursor: Optional[Union[str, int]] = None
    created_after: Optional[int] = Field(default=None, alias="createdAfter")
    created_before: Optional[int] = Field(default=None, alias="createdBefore")


class SandboxProcessListResponse(SandboxBaseModel):
    data: List[SandboxProcessSummary]
    next_cursor: Optional[str] = Field(default=None, alias="next_cursor")


class SandboxProcessWaitParams(SandboxBaseModel):
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")
    timeout_sec: Optional[int] = Field(default=None, alias="timeoutSec")


class SandboxProcessStdinParams(SandboxBaseModel):
    data: Optional[Union[str, bytes]] = None
    encoding: Optional[SandboxFileEncoding] = None
    eof: Optional[bool] = None


class SandboxProcessOutputEvent(SandboxBaseModel):
    type: Literal["stdout", "stderr", "system"]
    seq: int
    data: str
    timestamp: int


class SandboxProcessExitEvent(SandboxBaseModel):
    type: Literal["exit"]
    result: SandboxProcessResult


SandboxProcessStreamEvent = Union[SandboxProcessOutputEvent, SandboxProcessExitEvent]


class SandboxFileInfo(SandboxBaseModel):
    path: str
    name: str
    type: SandboxFileType
    size: int
    mode: int
    permissions: str
    owner: str
    group: str
    modified_time: Optional[datetime] = Field(default=None, alias="modifiedTime")
    symlink_target: Optional[str] = Field(default=None, alias="symlinkTarget")

    @field_validator("modified_time", mode="before")
    @classmethod
    def parse_modified_time(cls, value):
        return _parse_optional_datetime_from_millis(value)


class SandboxFileWriteInfo(SandboxBaseModel):
    path: str
    name: str
    type: Optional[SandboxFileType] = None


SandboxFileEntry = SandboxFileInfo


class SandboxFileListOptions(SandboxBaseModel):
    depth: Optional[int] = None


class SandboxFileListParams(SandboxBaseModel):
    path: str
    depth: Optional[int] = None


class SandboxFileListResponse(SandboxBaseModel):
    path: str
    depth: int
    entries: List[SandboxFileInfo]


class SandboxFileReadOptions(SandboxBaseModel):
    offset: Optional[int] = None
    length: Optional[int] = None
    format: Optional[SandboxFileReadFormat] = None


class SandboxFileReadParams(SandboxBaseModel):
    path: str
    offset: Optional[int] = None
    length: Optional[int] = None
    encoding: Optional[SandboxFileEncoding] = None


class SandboxFileReadResult(SandboxBaseModel):
    content: str
    encoding: SandboxFileEncoding
    bytes_read: int = Field(alias="bytesRead")
    truncated: bool
    content_type: Optional[str] = Field(default=None, alias="contentType")


SandboxFileWriteData = Union[str, bytes]


class SandboxFileWriteEntry(SandboxBaseModel):
    path: str
    data: SandboxFileWriteData


class SandboxFileTextWriteOptions(SandboxBaseModel):
    append: Optional[bool] = None
    mode: Optional[str] = None


class SandboxFileBytesWriteOptions(SandboxBaseModel):
    append: Optional[bool] = None
    mode: Optional[str] = None


class SandboxFileWriteTextParams(SandboxBaseModel):
    path: str
    data: str
    append: Optional[bool] = None
    mode: Optional[str] = None


class SandboxFileWriteBytesParams(SandboxBaseModel):
    path: str
    data: bytes
    append: Optional[bool] = None
    mode: Optional[str] = None


class SandboxFileWriteResult(SandboxBaseModel):
    files: List[SandboxFileWriteInfo]


class SandboxFileUploadParams(SandboxBaseModel):
    path: str
    data: Union[bytes, str]


class SandboxFileTransferResult(SandboxBaseModel):
    path: str
    bytes_written: int = Field(alias="bytesWritten")


class SandboxFileRemoveOptions(SandboxBaseModel):
    recursive: Optional[bool] = None


class SandboxFileDeleteParams(SandboxBaseModel):
    path: str
    recursive: Optional[bool] = None


class SandboxFileMakeDirOptions(SandboxBaseModel):
    parents: Optional[bool] = None
    mode: Optional[str] = None


class SandboxFileMkdirParams(SandboxBaseModel):
    path: str
    parents: Optional[bool] = None
    mode: Optional[str] = None


class SandboxFileMoveParams(SandboxBaseModel):
    source: str
    destination: str
    overwrite: Optional[bool] = None


class SandboxFileCopyParams(SandboxBaseModel):
    source: str
    destination: str
    recursive: Optional[bool] = None
    overwrite: Optional[bool] = None


class SandboxFileChmodParams(SandboxBaseModel):
    path: str
    mode: str
    recursive: Optional[bool] = None


class SandboxFileChownParams(SandboxBaseModel):
    path: str
    uid: Optional[int] = None
    gid: Optional[int] = None
    recursive: Optional[bool] = None


class SandboxFileMutationResult(SandboxBaseModel):
    path: str
    created: Optional[bool] = None


class SandboxFileMoveCopyResult(SandboxBaseModel):
    entry: SandboxFileInfo


class SandboxFileWatchParams(SandboxBaseModel):
    path: str
    recursive: Optional[bool] = None


class SandboxFileWatchEvent(SandboxBaseModel):
    seq: int
    path: str
    op: str
    timestamp: int


class SandboxFileWatchStatus(SandboxBaseModel):
    id: str
    path: str
    recursive: bool
    active: bool
    error: Optional[str] = None
    created_at: int = Field(alias="createdAt")
    stopped_at: Optional[int] = Field(default=None, alias="stoppedAt")
    oldest_seq: int = Field(default=0, alias="oldestSeq")
    last_seq: int = Field(default=0, alias="lastSeq")
    event_count: int = Field(default=0, alias="eventCount")
    events: Optional[List[SandboxFileWatchEvent]] = None


class SandboxFileWatchEventsParams(SandboxBaseModel):
    cursor: Optional[int] = None
    route: Optional[SandboxFileWatchRoute] = None


class SandboxFileWatchEventMessage(SandboxBaseModel):
    type: Literal["event"]
    event: SandboxFileWatchEvent


class SandboxFileWatchDoneEvent(SandboxBaseModel):
    type: Literal["done"]
    status: SandboxFileWatchStatus


SandboxFileWatchStreamEvent = Union[
    SandboxFileWatchEventMessage,
    SandboxFileWatchDoneEvent,
]


class SandboxFileSystemEvent(SandboxBaseModel):
    type: SandboxFileSystemEventType
    name: str


SandboxWatchDirExitCallback = Callable[[Optional[BaseException]], object]


class SandboxPresignFileParams(SandboxBaseModel):
    path: str
    expires_in_seconds: Optional[int] = Field(default=None, alias="expiresInSeconds")
    one_time: Optional[bool] = Field(default=None, alias="oneTime")


class SandboxPresignedUrl(SandboxBaseModel):
    token: str
    path: str
    method: str
    expires_at: int = Field(alias="expiresAt")
    url: str


class SandboxTerminalCreateParams(SandboxBaseModel):
    command: str
    args: Optional[List[str]] = None
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    use_shell: Optional[bool] = Field(default=None, alias="useShell")
    rows: Optional[int] = None
    cols: Optional[int] = None
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")


class SandboxTerminalOutputChunk(SandboxBaseModel):
    seq: int
    data: str
    raw: bytes
    timestamp: int


class SandboxTerminalStatus(SandboxBaseModel):
    id: str
    command: str
    args: Optional[List[str]] = None
    cwd: str
    pid: Optional[int] = None
    running: bool
    exit_code: Optional[int] = Field(default=None, alias="exitCode")
    error: Optional[str] = None
    timed_out: Optional[bool] = Field(default=None, alias="timedOut")
    rows: int
    cols: int
    started_at: int = Field(alias="startedAt")
    finished_at: Optional[int] = Field(default=None, alias="finishedAt")
    output: Optional[List[SandboxTerminalOutputChunk]] = None


class SandboxTerminalWaitParams(SandboxBaseModel):
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")
    include_output: Optional[bool] = Field(default=None, alias="includeOutput")


class SandboxTerminalKillParams(SandboxBaseModel):
    signal: Optional[str] = None
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")


class SandboxTerminalOutputEvent(SandboxBaseModel):
    type: Literal["output"]
    seq: int
    data: str
    raw: bytes
    timestamp: int


class SandboxTerminalExitEvent(SandboxBaseModel):
    type: Literal["exit"]
    status: SandboxTerminalStatus


SandboxTerminalEvent = Union[SandboxTerminalOutputEvent, SandboxTerminalExitEvent]
