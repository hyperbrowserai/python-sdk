from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

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


class JevComputerUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: List[Dict[str, Any]]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


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
