from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..consts import TaskLlm
from ..session import CreateSessionParams
from .browser_use import BrowserUseTaskStatus

TaskStatus = BrowserUseTaskStatus


class AgentTaskListParams(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    task: Optional[str] = Field(default=None, serialization_alias="task")
    page: Optional[int] = Field(default=None, serialization_alias="page")
    limit: Optional[int] = Field(default=None, serialization_alias="limit")


class AgentTaskSummary(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    id: str
    created_at: datetime = Field(alias="createdAt")
    status: TaskStatus
    task: str


class AgentTaskListResponse(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    tasks: List[AgentTaskSummary]
    total_count: int = Field(alias="totalCount")
    page: int
    per_page: int = Field(alias="perPage")


class StartTaskParams(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    task: str
    llm: Optional[TaskLlm] = Field(default=None, serialization_alias="llm")
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
    planner_llm: Optional[TaskLlm] = Field(
        default=None, serialization_alias="plannerLlm"
    )
    page_extraction_llm: Optional[TaskLlm] = Field(
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


class StartTaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    job_id: str = Field(alias="jobId")


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    status: TaskStatus


class TaskMetadata(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    input_tokens: Optional[int] = Field(default=None, alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, alias="outputTokens")
    num_task_steps_completed: Optional[int] = Field(
        default=None, alias="numTaskStepsCompleted"
    )


class TaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_alias=True)

    job_id: str = Field(alias="jobId")
    status: TaskStatus
    metadata: Optional[TaskMetadata] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
