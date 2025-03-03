from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from .consts import Llm
from .session import CreateSessionParams

TaskJobStatus = Literal["pending", "running", "completed", "failed", "stopped"]


class StartTaskJobParams(BaseModel):
    """
    Parameters for creating a new task job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    llm: Optional[Llm] = Field(default=None, serialization_alias="llm")
    session_id: Optional[str] = Field(default=None, serialization_alias="sessionId")
    validate_output: Optional[bool] = Field(
        default=None, serialization_alias="validateOutput"
    )
    use_vision: Optional[bool] = Field(default=None, serialization_alias="useVision")
    use_vision_for_planner: Optional[bool] = Field(
        default=None, serialization_alias="useVisionForPlanner"
    )
    max_actions_per_step: Optional[int] = Field(
        default=None, serialization_alias="maxActionsPerStep"
    )
    max_input_tokens: Optional[int] = Field(
        default=None, serialization_alias="maxInputTokens"
    )
    planner_llm: Optional[Llm] = Field(default=None, serialization_alias="plannerLlm")
    page_extraction_llm: Optional[Llm] = Field(
        default=None, serialization_alias="pageExtractionLlm"
    )
    planner_interval: Optional[int] = Field(
        default=None, serialization_alias="plannerInterval"
    )
    max_steps: Optional[int] = Field(default=None, serialization_alias="maxSteps")
    keep_browser_open: Optional[bool] = Field(
        default=None, serialization_alias="keepBrowserOpen"
    )
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
    )


class StartTaskJobResponse(BaseModel):
    """
    Response from starting a task job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class TaskJobStatusResponse(BaseModel):
    """
    Response from getting a task job status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: TaskJobStatus


class TaskJobResponse(BaseModel):
    """
    Response from a task job.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: TaskJobStatus
    data: Optional[dict] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
