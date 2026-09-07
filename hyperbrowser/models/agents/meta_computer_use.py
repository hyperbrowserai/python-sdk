from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .cua import CuaStepIncompleteDetails, CuaStepResponseError
from ..session import CreateSessionParams
from ..consts import MetaComputerUseLlm, MetaReasoningEffort

MetaComputerUseTaskStatus = Literal[
    "pending", "running", "completed", "failed", "stopped"
]


class MetaComputerUseApiKeys(BaseModel):
    """
    API keys for the Meta Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    meta: Optional[str] = Field(default=None, serialization_alias="meta")


class StartMetaComputerUseTaskParams(BaseModel):
    """
    Parameters for creating a new Meta Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    llm: Optional[MetaComputerUseLlm] = Field(default=None, serialization_alias="llm")
    reasoning_effort: Optional[MetaReasoningEffort] = Field(
        default=None, serialization_alias="reasoningEffort"
    )
    session_id: Optional[str] = Field(default=None, serialization_alias="sessionId")
    max_failures: Optional[int] = Field(default=None, serialization_alias="maxFailures")
    max_steps: Optional[int] = Field(default=None, serialization_alias="maxSteps")
    keep_browser_open: Optional[bool] = Field(
        default=None, serialization_alias="keepBrowserOpen"
    )
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )
    use_custom_api_keys: Optional[bool] = Field(
        default=None, serialization_alias="useCustomApiKeys"
    )
    api_keys: Optional[MetaComputerUseApiKeys] = Field(
        default=None, serialization_alias="apiKeys"
    )
    use_computer_action: Optional[bool] = Field(
        default=None, serialization_alias="useComputerAction"
    )


class StartMetaComputerUseTaskResponse(BaseModel):
    """
    Response from starting a Meta Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class MetaComputerUseTaskStatusResponse(BaseModel):
    """
    Response from getting a Meta Computer Use task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: MetaComputerUseTaskStatus


class MetaComputerUseStepReasoning(BaseModel):
    """
    Reasoning metadata on a compacted Meta Computer Use step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    effort: Optional[str] = Field(default=None, serialization_alias="effort")
    summary: Optional[str] = Field(default=None, serialization_alias="summary")


class MetaComputerUseStepResponse(BaseModel):
    """
    Response from a single Meta Computer Use step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    created_at: Optional[int] = Field(default=None, serialization_alias="created_at")
    completed_at: Optional[int] = Field(
        default=None, serialization_alias="completed_at"
    )
    output_text: Optional[str] = Field(default=None, serialization_alias="output_text")
    error: Optional[CuaStepResponseError] = Field(
        default=None, serialization_alias="error"
    )
    incomplete_details: Optional[CuaStepIncompleteDetails] = Field(
        default=None, serialization_alias="incomplete_details"
    )
    model: Optional[str] = Field(default=None, serialization_alias="model")
    output: Optional[List[Any]] = Field(default=None, serialization_alias="output")
    reasoning: Optional[MetaComputerUseStepReasoning] = Field(
        default=None, serialization_alias="reasoning"
    )
    status: Optional[str] = Field(default=None, serialization_alias="status")


class MetaComputerUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: List[MetaComputerUseStepResponse]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class MetaComputerUseTaskMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    input_tokens: Optional[int] = Field(default=None, alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, alias="outputTokens")
    num_task_steps_completed: Optional[int] = Field(
        default=None, alias="numTaskStepsCompleted"
    )


class MetaComputerUseTaskResponse(BaseModel):
    """
    Response from a Meta Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: MetaComputerUseTaskStatus
    metadata: Optional[MetaComputerUseTaskMetadata] = Field(
        default=None, alias="metadata"
    )
    data: Optional[MetaComputerUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
