from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..session import CreateSessionParams
from ..consts import GeminiComputerUseLlm

GeminiComputerUseTaskStatus = Literal[
    "pending", "running", "completed", "failed", "stopped"
]


class GeminiComputerUseApiKeys(BaseModel):
    """
    API keys for the Gemini Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    google: Optional[str] = Field(default=None, serialization_alias="google")


class StartGeminiComputerUseTaskParams(BaseModel):
    """
    Parameters for creating a new Gemini Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    llm: Optional[GeminiComputerUseLlm] = Field(default=None, serialization_alias="llm")
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
    use_computer_action: Optional[bool] = Field(
        default=None, serialization_alias="useComputerAction"
    )
    api_keys: Optional[GeminiComputerUseApiKeys] = Field(
        default=None, serialization_alias="apiKeys"
    )


class StartGeminiComputerUseTaskResponse(BaseModel):
    """
    Response from starting a Gemini Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class GeminiComputerUseTaskStatusResponse(BaseModel):
    """
    Response from getting a Gemini Computer Use task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: GeminiComputerUseTaskStatus


class GeminiComputerUseStepResponse(BaseModel):
    """
    Response from a single Gemini Computer Use step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    candidates: Optional[list[Any]] = Field(
        default=None, serialization_alias="candidates"
    )
    model_version: Optional[str] = Field(
        default=None, serialization_alias="modelVersion"
    )


class GeminiComputerUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[GeminiComputerUseStepResponse]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class GeminiComputerUseTaskResponse(BaseModel):
    """
    Response from a Gemini Computer Use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: GeminiComputerUseTaskStatus
    data: Optional[GeminiComputerUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
