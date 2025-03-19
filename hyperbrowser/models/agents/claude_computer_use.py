from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..session import CreateSessionParams

ClaudeComputerUseTaskStatus = Literal[
    "pending", "running", "completed", "failed", "stopped"
]


class StartClaudeComputerUseTaskParams(BaseModel):
    """
    Parameters for creating a new Claude Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    session_id: Optional[str] = Field(default=None, serialization_alias="sessionId")
    max_failures: Optional[int] = Field(default=None, serialization_alias="maxFailures")
    max_steps: Optional[int] = Field(default=None, serialization_alias="maxSteps")
    keep_browser_open: Optional[bool] = Field(
        default=None, serialization_alias="keepBrowserOpen"
    )
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )


class StartClaudeComputerUseTaskResponse(BaseModel):
    """
    Response from starting a Claude Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class ClaudeComputerUseTaskStatusResponse(BaseModel):
    """
    Response from getting a Claude Computer Use task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: ClaudeComputerUseTaskStatus


class ClaudeComputerUseStepResponse(BaseModel):
    """
    Response from a single Claude Computer Use step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    role: str
    type: str
    model: str
    content: list[Any]
    stop_reason: Optional[str] = Field(default=None)
    stop_sequence: Optional[str] = Field(default=None)


class ClaudeComputerUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[ClaudeComputerUseStepResponse]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class ClaudeComputerUseTaskResponse(BaseModel):
    """
    Response from a Claude Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: ClaudeComputerUseTaskStatus
    data: Optional[ClaudeComputerUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
