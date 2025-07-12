from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ComputerAction(str, Enum):
    """Computer action types."""

    CLICK = "click"
    DRAG = "drag"
    PRESS_KEYS = "press_keys"
    MOVE_MOUSE = "move_mouse"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    TYPE_TEXT = "type_text"


class Coordinate(BaseModel):
    """Coordinate model for drag actions."""

    x: int
    y: int


class ClickActionParams(BaseModel):
    """Parameters for click action."""

    model_config = ConfigDict(use_enum_values=True)

    action: Literal[ComputerAction.CLICK] = ComputerAction.CLICK
    x: int
    y: int
    button: Literal["left", "right", "middle", "back", "forward", "wheel"] = Field(
        default="left"
    )
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


ComputerActionParams = Union[
    ClickActionParams,
    DragActionParams,
    PressKeysActionParams,
    MoveMouseActionParams,
    ScreenshotActionParams,
    ScrollActionParams,
    TypeTextActionParams,
]


class ComputerActionResponse(BaseModel):
    """Response from computer action API."""

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    success: bool
    screenshot: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
