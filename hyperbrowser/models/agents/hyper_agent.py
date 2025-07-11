from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..consts import HyperAgentLlm
from ..session import CreateSessionParams

HyperAgentTaskStatus = Literal["pending", "running", "completed", "failed", "stopped"]


class HyperAgentApiKeys(BaseModel):
    """
    API keys for the HyperAgent task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    openai: Optional[str] = Field(default=None, serialization_alias="openai")
    anthropic: Optional[str] = Field(default=None, serialization_alias="anthropic")
    google: Optional[str] = Field(default=None, serialization_alias="google")


class StartHyperAgentTaskParams(BaseModel):
    """
    Parameters for creating a new HyperAgent task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    llm: Optional[HyperAgentLlm] = Field(default=None, serialization_alias="llm")
    session_id: Optional[str] = Field(default=None, serialization_alias="sessionId")
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
    api_keys: Optional[HyperAgentApiKeys] = Field(
        default=None, serialization_alias="apiKeys"
    )


class StartHyperAgentTaskResponse(BaseModel):
    """
    Response from starting a HyperAgent task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class HyperAgentTaskStatusResponse(BaseModel):
    """
    Response from getting a HyperAgent task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: HyperAgentTaskStatus


class HyperAgentActionOutput(BaseModel):
    """
    The output of an action in a HyperAgent step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    success: bool
    message: str
    extract: Optional[Dict[str, Any]] = Field(default=None)


class HyperAgentOutput(BaseModel):
    """
    The output of a HyperAgent step.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    thoughts: Optional[str] = Field(default=None)
    memory: Optional[str] = Field(default=None)
    next_goal: Optional[str] = Field(default=None, alias="nextGoal")
    actions: List[Dict[str, Any]] = Field(default=[])


class HyperAgentStep(BaseModel):
    """
    A single step in a HyperAgent task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    idx: int
    agent_output: HyperAgentOutput = Field(alias="agentOutput")
    action_outputs: List[HyperAgentActionOutput] = Field(alias="actionOutputs")


class HyperAgentTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[HyperAgentStep]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class HyperAgentTaskResponse(BaseModel):
    """
    Response from a HyperAgent task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: HyperAgentTaskStatus
    data: Optional[HyperAgentTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
