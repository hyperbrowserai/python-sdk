from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ..consts import HyperAgentLlm, HyperAgentVersion
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

    version: Optional[HyperAgentVersion] = Field(
        default=None, serialization_alias="version"
    )
    task: str
    llm: Optional[HyperAgentLlm] = Field(default=None, serialization_alias="llm")
    session_id: Optional[str] = Field(default=None, serialization_alias="sessionId")
    max_steps: Optional[int] = Field(default=None, serialization_alias="maxSteps")
    enable_visual_mode: Optional[bool] = Field(
        default=None, serialization_alias="enableVisualMode"
    )
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


class HyperAgentOutputV110(BaseModel):
    """
    The output of a HyperAgent step v1.1.0.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    thoughts: Optional[str] = Field(default=None)
    memory: Optional[str] = Field(default=None)
    action: Optional[Dict[str, Any]] = Field(default=None)


class HyperAgentStepV110(BaseModel):
    """
    A single step in a HyperAgent task v1.1.0.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    idx: int
    agent_output: HyperAgentOutputV110 = Field(alias="agentOutput")
    action_output: HyperAgentActionOutput = Field(alias="actionOutput")


class HyperAgentTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[Union[HyperAgentStep, HyperAgentStepV110]]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class HyperAgentTaskMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    num_task_steps_completed: Optional[int] = Field(
        default=None, alias="numTaskStepsCompleted"
    )


class HyperAgentTaskResponse(BaseModel):
    """
    Response from a HyperAgent task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: HyperAgentTaskStatus
    metadata: Optional[HyperAgentTaskMetadata] = Field(default=None, alias="metadata")
    data: Optional[HyperAgentTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
