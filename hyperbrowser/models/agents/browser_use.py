from typing import Any, Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, Field

from ..consts import BrowserUseLlm, BrowserUseVersion
from ..session import CreateSessionParams

BrowserUseTaskStatus = Literal["pending", "running", "completed", "failed", "stopped"]


class BrowserUseApiKeys(BaseModel):
    """
    API keys for the browser use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    openai: Optional[str] = Field(default=None, serialization_alias="openai")
    anthropic: Optional[str] = Field(default=None, serialization_alias="anthropic")
    google: Optional[str] = Field(default=None, serialization_alias="google")


class StartBrowserUseTaskParams(BaseModel):
    """
    Parameters for creating a new browser use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
    version: Optional[BrowserUseVersion] = Field(
        default=None, serialization_alias="version"
    )
    llm: Optional[BrowserUseLlm] = Field(default=None, serialization_alias="llm")
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
    planner_llm: Optional[BrowserUseLlm] = Field(
        default=None, serialization_alias="plannerLlm"
    )
    page_extraction_llm: Optional[BrowserUseLlm] = Field(
        default=None, serialization_alias="pageExtractionLlm"
    )
    planner_interval: Optional[int] = Field(
        default=None, serialization_alias="plannerInterval"
    )
    max_steps: Optional[int] = Field(default=None, serialization_alias="maxSteps")
    max_failures: Optional[int] = Field(default=None, serialization_alias="maxFailures")
    initial_actions: Optional[List[Dict[str, Dict[str, Any]]]] = Field(
        default=None, serialization_alias="initialActions"
    )
    sensitive_data: Optional[Dict[str, str]] = Field(
        default=None, serialization_alias="sensitiveData"
    )
    message_context: Optional[str] = Field(
        default=None, serialization_alias="messageContext"
    )
    output_model_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = Field(
        default=None, serialization_alias="outputModelSchema"
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
    api_keys: Optional[BrowserUseApiKeys] = Field(
        default=None, serialization_alias="apiKeys"
    )


class StartBrowserUseTaskResponse(BaseModel):
    """
    Response from starting a browser use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


class BrowserUseTaskStatusResponse(BaseModel):
    """
    Response from getting a browser use task status.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: BrowserUseTaskStatus


class BrowserUseAgentBrain(BaseModel):
    evaluation_previous_goal: str
    memory: str
    next_goal: str


class BrowserUseAgentOutput(BaseModel):
    current_state: BrowserUseAgentBrain
    action: list[dict]


class BrowserUseActionResult(BaseModel):
    is_done: Optional[bool] = False
    success: Optional[bool] = None
    extracted_content: Optional[str] = None
    error: Optional[str] = None
    include_in_memory: bool = False


class BrowserUseStepMetadata(BaseModel):
    step_start_time: float
    step_end_time: float
    input_tokens: int
    step_number: int


class BrowserUseTabInfo(BaseModel):
    page_id: int
    url: str
    title: str


class BrowserUseCoordinates(BaseModel):
    x: int
    y: int


class BrowserUseCoordinateSet(BaseModel):
    top_left: BrowserUseCoordinates
    top_right: BrowserUseCoordinates
    bottom_left: BrowserUseCoordinates
    bottom_right: BrowserUseCoordinates
    center: BrowserUseCoordinates
    width: int
    height: int


class BrowserUseViewportInfo(BaseModel):
    scroll_x: int
    scroll_y: int
    width: int
    height: int


class BrowserUseDOMHistoryElement(BaseModel):
    tag_name: str
    xpath: str
    highlight_index: Optional[int]
    entire_parent_branch_path: list[str]
    attributes: dict[str, str]
    shadow_root: bool = False
    css_selector: Optional[str] = None
    page_coordinates: Optional[BrowserUseCoordinateSet] = None
    viewport_coordinates: Optional[BrowserUseCoordinateSet] = None
    viewport_info: Optional[BrowserUseViewportInfo] = None


class BrowserUseBrowserStateHistory(BaseModel):
    url: str
    title: str
    tabs: list[BrowserUseTabInfo]
    interacted_element: Union[
        list[Union[BrowserUseDOMHistoryElement, None]], list[None]
    ]
    screenshot: Optional[str] = None


class BrowserUseAgentHistory(BaseModel):
    model_output: Union[BrowserUseAgentOutput, None]
    result: list[BrowserUseActionResult]
    state: BrowserUseBrowserStateHistory
    metadata: Optional[BrowserUseStepMetadata] = None


# ===== 0.7.10-specific response models =====


class BrowserUseAgentOutputV0710(BaseModel):
    thinking: Optional[str] = None
    evaluation_previous_goal: Optional[str] = None
    memory: Optional[str] = None
    next_goal: Optional[str] = None
    action: list[dict]


class BrowserUseActionResultV0710(BaseModel):
    is_done: Optional[bool] = False
    success: Optional[bool] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None
    attachments: Optional[list[str]] = None
    long_term_memory: Optional[str] = None
    extracted_content: Optional[str] = None
    include_extracted_content_only_once: Optional[bool] = False
    include_in_memory: bool = False


class BrowserUseBrowserStateHistoryV0710(BaseModel):
    url: str
    title: str
    tabs: list[dict]
    interacted_element: Union[list[Union[dict, None]], list[None]]


class BrowserUseStepMetadataV0710(BaseModel):
    step_start_time: float
    step_end_time: float
    step_number: int


class BrowserUseAgentHistoryV0710(BaseModel):
    model_output: Union[BrowserUseAgentOutputV0710, None]
    result: list[BrowserUseActionResultV0710]
    state: BrowserUseBrowserStateHistoryV0710
    metadata: Optional[BrowserUseStepMetadataV0710] = None


# ===== latest response models =====

BrowserUseAgentHistoryLatest = Dict[str, Any]

BrowserUseStep = Union[
    BrowserUseAgentHistory, BrowserUseAgentHistoryV0710, BrowserUseAgentHistoryLatest
]


class BrowserUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[BrowserUseStep]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class BrowserUseTaskMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    input_tokens: Optional[int] = Field(default=None, alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, alias="outputTokens")
    num_task_steps_completed: Optional[int] = Field(
        default=None, alias="numTaskStepsCompleted"
    )


class BrowserUseTaskResponse(BaseModel):
    """
    Response from a browser use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: BrowserUseTaskStatus
    metadata: Optional[BrowserUseTaskMetadata] = Field(default=None, alias="metadata")
    data: Optional[BrowserUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")


def cast_steps_for_version(
    steps: List[BrowserUseStep], version: BrowserUseVersion
) -> List[BrowserUseStep]:
    if version == "0.1.40":
        return [BrowserUseAgentHistory.model_validate(s) for s in steps]
    elif version == "0.7.10":
        return [BrowserUseAgentHistoryV0710.model_validate(s) for s in steps]
    elif version == "latest":
        return steps
    else:
        raise ValueError(f"Invalid version: {version}")
