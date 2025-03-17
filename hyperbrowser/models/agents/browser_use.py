from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ..consts import BrowserUseLlm
from ..session import CreateSessionParams

BrowserUseTaskStatus = Literal["pending", "running", "completed", "failed", "stopped"]


class StartBrowserUseTaskParams(BaseModel):
    """
    Parameters for creating a new browser use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    task: str
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
    keep_browser_open: Optional[bool] = Field(
        default=None, serialization_alias="keepBrowserOpen"
    )
    session_options: Optional[CreateSessionParams] = Field(
        default=None, serialization_alias="sessionOptions"
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


class BrowserUseTaskData(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    steps: list[BrowserUseAgentHistory]
    final_result: Optional[str] = Field(default=None, alias="finalResult")


class BrowserUseTaskResponse(BaseModel):
    """
    Response from a browser use task.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: BrowserUseTaskStatus
    data: Optional[BrowserUseTaskData] = Field(default=None, alias="data")
    error: Optional[str] = Field(default=None, alias="error")
    live_url: Optional[str] = Field(default=None, alias="liveUrl")
