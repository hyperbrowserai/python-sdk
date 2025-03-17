from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..session import CreateSessionParams

CuaTaskStatus = Literal["pending", "running", "completed", "failed", "stopped"]


class StartCuaTaskParams(BaseModel):
    """
    Parameters for creating a new CUA task.
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


class StartCuaTaskResponse(BaseModel):
    """
    Response from starting a CUA task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class CuaTaskStatusResponse(BaseModel):
    """
    Response from getting a CUA task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: CuaTaskStatus


class CuaStepResponseError(BaseModel):
    """
    Error details for a CUA step response.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    code: str
    message: str


class CuaStepIncompleteDetails(BaseModel):
    """
    Details about why a CUA step is incomplete.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    reason: Optional[str] = Field(default=None)


class CuaStepReasoning(BaseModel):
    """
    Reasoning information for a CUA step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    effort: Optional[str] = Field(default=None)
    generate_summary: Optional[str] = Field(default=None)


class CuaStepResponse(BaseModel):
    """
    Response from a single CUA step.
    """

    created_at: int
    output_text: str
    error: Optional[CuaStepResponseError] = None
    incomplete_details: Optional[CuaStepIncompleteDetails] = None
    model: str
    output: list[Any]
    reasoning: Optional[CuaStepReasoning] = None
    status: Optional[str] = None


class CuaTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[CuaStepResponse]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class CuaTaskResponse(BaseModel):
    """
    Response from a CUA task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: CuaTaskStatus
    data: Optional[CuaTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
