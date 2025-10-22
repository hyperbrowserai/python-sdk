from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ComputerAction(str, Enum):
    """Computer action types."""

    CLICK = "click"
    DRAG = "drag"
    HOLD_KEY = "hold_key"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOVE_MOUSE = "move_mouse"
    PRESS_KEYS = "press_keys"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    TYPE_TEXT = "type_text"
    GET_CLIPBOARD_TEXT = "get_clipboard_text"


ComputerActionMouseButton = Literal[
    "left", "right", "middle", "back", "forward", "wheel"
]


class Coordinate(BaseModel):
    """Coordinate model for drag actions."""

    x: int
    y: int


class ClickActionParams(BaseModel):
    """Parameters for click action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.CLICK] = ComputerAction.CLICK
    x: Optional[int] = Field(default=None)
    y: Optional[int] = Field(default=None)
    button: ComputerActionMouseButton = Field(default="left")
    num_clicks: int = Field(serialization_alias="numClicks", default=1)
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class DragActionParams(BaseModel):
    """Parameters for drag action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.DRAG] = ComputerAction.DRAG
    path: List[Coordinate]
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class PressKeysActionParams(BaseModel):
    """Parameters for press keys action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.PRESS_KEYS] = ComputerAction.PRESS_KEYS
    keys: List[str]
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class HoldKeyActionParams(BaseModel):
    """Parameters for hold key action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.HOLD_KEY] = ComputerAction.HOLD_KEY
    key: str
    duration: int
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class MouseDownActionParams(BaseModel):
    """Parameters for mouse down action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.MOUSE_DOWN] = ComputerAction.MOUSE_DOWN
    button: ComputerActionMouseButton = Field(default="left")
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class MouseUpActionParams(BaseModel):
    """Parameters for mouse up action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.MOUSE_UP] = ComputerAction.MOUSE_UP
    button: ComputerActionMouseButton = Field(default="left")
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class MoveMouseActionParams(BaseModel):
    """Parameters for move mouse action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.MOVE_MOUSE] = ComputerAction.MOVE_MOUSE
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class ScreenshotActionParams(BaseModel):
    """Parameters for screenshot action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.SCREENSHOT] = ComputerAction.SCREENSHOT


class ScrollActionParams(BaseModel):
    """Parameters for scroll action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.SCROLL] = ComputerAction.SCROLL
    x: int
    y: int
    scroll_x: int = Field(serialization_alias="scrollX")
    scroll_y: int = Field(serialization_alias="scrollY")
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class TypeTextActionParams(BaseModel):
    """Parameters for type text action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.TYPE_TEXT] = ComputerAction.TYPE_TEXT
    text: str
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


class GetClipboardTextActionParams(BaseModel):
    """Parameters for get clipboard text action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.GET_CLIPBOARD_TEXT] = (
        ComputerAction.GET_CLIPBOARD_TEXT
    )
    return_screenshot: bool = Field(
        serialization_alias="returnScreenshot", default=False
    )


ComputerActionParams = Union[
    ClickActionParams,
    DragActionParams,
    PressKeysActionParams,
    MoveMouseActionParams,
    ScreenshotActionParams,
    ScrollActionParams,
    TypeTextActionParams,
    HoldKeyActionParams,
    MouseDownActionParams,
    MouseUpActionParams,
    GetClipboardTextActionParams,
]


class ComputerActionResponseDataClipboardText(BaseModel):
    """Data for get clipboard text action."""

    model_config = ConfigDict(populate_by_alias=True)

    clipboard_text: Optional[str] = Field(default=None, alias="clipboardText")


ComputerActionResponseData = Union[ComputerActionResponseDataClipboardText]


class ComputerActionResponse(BaseModel):
    """Response from computer action API."""

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    success: bool
    screenshot: Optional[str] = None
    data: Optional[ComputerActionResponseData] = None
    error: Optional[str] = None
    message: Optional[str] = None
