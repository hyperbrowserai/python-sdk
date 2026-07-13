from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..session import CreateSessionParams
from ..consts import GrokComputerUseLlm, GrokReasoningEffort

GrokComputerUseTaskStatus = Literal[
    "pending", "running", "completed", "failed", "stopped"
]


class GrokComputerUseApiKeys(BaseModel):
    """
    API keys for the Grok Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    xai: Optional[str] = Field(default=None, serialization_alias="xai")


class StartGrokComputerUseTaskParams(BaseModel):
    """
    Parameters for creating a new Grok Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    llm: Optional[GrokComputerUseLlm] = Field(default=None, serialization_alias="llm")
    reasoning_effort: Optional[GrokReasoningEffort] = Field(
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
    api_keys: Optional[GrokComputerUseApiKeys] = Field(
        default=None, serialization_alias="apiKeys"
    )
    use_computer_action: Optional[bool] = Field(
        default=None, serialization_alias="useComputerAction"
    )


class StartGrokComputerUseTaskResponse(BaseModel):
    """
    Response from starting a Grok Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class GrokComputerUseTaskStatusResponse(BaseModel):
    """
    Response from getting a Grok Computer Use task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: GrokComputerUseTaskStatus


class GrokComputerUseStepResponse(BaseModel):
    """
    Response from a single Grok Computer Use step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    created_at: Optional[str] = Field(default=None, serialization_alias="created_at")
    completed_at: Optional[str] = Field(default=None, serialization_alias="completed_at")
    output_text: Optional[str] = Field(default=None, serialization_alias="output_text")
    error: Optional[str] = Field(default=None, serialization_alias="error")
    incomplete_details: Optional[Any] = Field(
        default=None, serialization_alias="incomplete_details"
    )
    model: Optional[str] = Field(default=None, serialization_alias="model")
    output: Optional[list[Any]] = Field(default=None, serialization_alias="output")
    reasoning: Optional[Any] = Field(default=None, serialization_alias="reasoning")
    status: Optional[str] = Field(default=None, serialization_alias="status")


class GrokComputerUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[GrokComputerUseStepResponse]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class GrokComputerUseTaskMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    input_tokens: Optional[int] = Field(default=None, alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, alias="outputTokens")
    num_task_steps_completed: Optional[int] = Field(
        default=None, alias="numTaskStepsCompleted"
    )


class GrokComputerUseTaskResponse(BaseModel):
    """
    Response from a Grok Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: GrokComputerUseTaskStatus
    metadata: Optional[GrokComputerUseTaskMetadata] = Field(
        default=None, alias="metadata"
    )
    data: Optional[GrokComputerUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
