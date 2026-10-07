"""WebMCP request models and page-tool discovery/invocation responses."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class WebMCPInvokeParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tool_ref: str = Field(min_length=1, max_length=4096, serialization_alias="toolRef")
    input: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(
        default=60, ge=1, le=120, strict=True, serialization_alias="timeoutSeconds"
    )


class WebMCPStartParams(WebMCPInvokeParams):
    timeout_seconds: int = Field(
        default=300, ge=1, le=3600, strict=True, serialization_alias="timeoutSeconds"
    )


class WebMCPResultParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    wait_seconds: int = Field(
        default=0, ge=0, le=30, strict=True, serialization_alias="waitSeconds"
    )


class WebMCPAnnotations(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    read_only: bool = Field(alias="readOnly")
    untrusted_content: bool = Field(alias="untrustedContent")
    consequential: bool
    autosubmit: bool
    destructive: Optional[bool] = None
    idempotent: Optional[bool] = None
    open_world: Optional[bool] = Field(default=None, alias="openWorld")


class WebMCPFrame(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    url: str
    is_main_frame: bool = Field(alias="isMainFrame")


class WebMCPSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: Literal["native", "polyfill"]
    tab_id: str = Field(alias="tabId")
    page_url: str = Field(alias="pageUrl")
    page_title: str = Field(alias="pageTitle")
    frame: WebMCPFrame


class WebMCPTool(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool_ref: str = Field(alias="toolRef")
    name: str
    title: Optional[str] = None
    description: str
    input_schema: Optional[Dict[str, Any]] = Field(default=None, alias="inputSchema")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, alias="outputSchema")
    annotations: WebMCPAnnotations
    declarative: bool
    backend_node_id: Optional[int] = Field(default=None, alias="backendNodeId")
    source: WebMCPSource


class WebMCPToolsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tools: List[WebMCPTool]
    native_supported: bool = Field(alias="nativeSupported")
    truncated: bool


WebMCPInvokeStatus = Literal["completed", "error", "canceled", "awaiting_submission"]
WebMCPInvocationStatus = Literal[
    "running",
    "awaiting_submission",
    "completed",
    "error",
    "canceled",
    "outcome_unknown",
]


class WebMCPInvokeResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    invocation_id: Optional[str] = Field(default=None, alias="invocationId")
    status: WebMCPInvokeStatus
    output: Any = None
    error_text: Optional[str] = Field(default=None, alias="errorText")
    output_bytes: int = Field(alias="outputBytes")
    output_truncated: bool = Field(default=False, alias="outputTruncated")
    output_preview: Optional[str] = Field(default=None, alias="outputPreview")
    untrusted_content: bool = Field(alias="untrustedContent")
    duration_ms: int = Field(alias="durationMs")


class WebMCPInvocationError(BaseModel):
    code: str
    message: str


class WebMCPInvocation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    invocation_id: str = Field(alias="invocationId")
    tool_ref: str = Field(alias="toolRef")
    status: WebMCPInvocationStatus
    cancellation_requested: bool = Field(alias="cancellationRequested")
    created_at: datetime = Field(alias="createdAt")
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")
    result: Optional[WebMCPInvokeResult] = None
    error: Optional[WebMCPInvocationError] = None
