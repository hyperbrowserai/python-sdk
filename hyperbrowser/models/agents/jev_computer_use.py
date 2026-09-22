from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..session import CreateSessionParams
from ..consts import JevComputerUseLlm, JevTextLlm

JevComputerUseTaskStatus = Literal[
    "pending", "running", "completed", "failed", "stopped"
]


class JevComputerUseApiKeys(BaseModel):
    """
    API keys for the Jev Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    jev: Optional[str] = Field(default=None, serialization_alias="jev")
    google: Optional[str] = Field(default=None, serialization_alias="google")


class StartJevComputerUseTaskParams(BaseModel):
    """
    Parameters for creating a new Jev Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    llm: Optional[JevComputerUseLlm] = Field(default=None, serialization_alias="llm")
    text_llm: Optional[JevTextLlm] = Field(default=None, serialization_alias="textLlm")
    start_url: Optional[str] = Field(default=None, serialization_alias="startUrl")
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
    api_keys: Optional[JevComputerUseApiKeys] = Field(
        default=None, serialization_alias="apiKeys"
    )
    use_computer_action: Optional[bool] = Field(
        default=None, serialization_alias="useComputerAction"
    )


class StartJevComputerUseTaskResponse(BaseModel):
    """
    Response from starting a Jev Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class JevComputerUseTaskStatusResponse(BaseModel):
    """
    Response from getting a Jev Computer Use task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: JevComputerUseTaskStatus


class JevComputerUseAction(BaseModel):
    """
    A single Jev action recorded during a task step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    kind: str
    target: Optional[str] = None
    option: Optional[str] = None


class JevComputerUseStepResponse(BaseModel):
    """
    Response from a single Jev Computer Use step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    step: int
    action: JevComputerUseAction
    url: str
    value: Optional[str] = None
    title: Optional[str] = None
    page_text: Optional[str] = Field(default=None, alias="pageText")
    target_description: Optional[str] = Field(default=None, alias="targetDescription")
    confidence: Optional[float] = None
    error: Optional[str] = None
    error_kind: Optional[str] = Field(default=None, alias="errorKind")
    page_changed: Optional[bool] = Field(default=None, alias="pageChanged")
    outcome: Optional[str] = None
    after: Optional[str] = None
    before_tab: Optional[str] = Field(default=None, alias="beforeTab")
    after_tab: Optional[str] = Field(default=None, alias="afterTab")
    before_observation: Optional[int] = Field(default=None, alias="beforeObservation")
    after_observation: Optional[int] = Field(default=None, alias="afterObservation")


class JevComputerUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: List[JevComputerUseStepResponse]
    final_result: Optional[str] = Field(default=None, alias="finalResult")
    reached_max_steps: Optional[bool] = Field(default=None, alias="reachedMaxSteps")
    final_url: Optional[str] = Field(default=None, alias="finalUrl")
    warnings: Optional[List[str]] = None


class JevComputerUseTaskMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    input_tokens: Optional[int] = Field(default=None, alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, alias="outputTokens")
    num_task_steps_completed: Optional[int] = Field(
        default=None, alias="numTaskStepsCompleted"
    )


class JevComputerUseTaskResponse(BaseModel):
    """
    Response from a Jev Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: JevComputerUseTaskStatus
    metadata: Optional[JevComputerUseTaskMetadata] = Field(
        default=None, alias="metadata"
    )
    data: Optional[JevComputerUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
