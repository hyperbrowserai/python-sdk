from typing import List, Literal, Optional, Union

from typing_extensions import Required, TypeAlias, TypedDict


ComputerActionMouseButton: TypeAlias = Literal[
    "left", "right", "middle", "back", "forward", "wheel"
]


class Coordinate(TypedDict):
    """A screen coordinate in pixels."""

    x: int
    y: int


class ClickActionParams(TypedDict, total=False):
    """Parameters for a mouse click action."""

    action: Required[Literal["click"]]
    x: Optional[int]
    y: Optional[int]
    button: ComputerActionMouseButton
    num_clicks: int
    return_screenshot: bool


class DragActionParams(TypedDict, total=False):
    """Parameters for dragging through a sequence of coordinates."""

    action: Required[Literal["drag"]]
    path: Required[List[Coordinate]]
    return_screenshot: bool


class PressKeysActionParams(TypedDict, total=False):
    """Parameters for pressing a key combination."""

    action: Required[Literal["press_keys"]]
    keys: Required[List[str]]
    return_screenshot: bool


class HoldKeyActionParams(TypedDict, total=False):
    """Parameters for holding a key for a duration."""

    action: Required[Literal["hold_key"]]
    key: Required[str]
    duration: Required[int]
    return_screenshot: bool


class MouseDownActionParams(TypedDict, total=False):
    """Parameters for pressing and holding a mouse button."""

    action: Required[Literal["mouse_down"]]
    button: ComputerActionMouseButton
    return_screenshot: bool


class MouseUpActionParams(TypedDict, total=False):
    """Parameters for releasing a mouse button."""

    action: Required[Literal["mouse_up"]]
    button: ComputerActionMouseButton
    return_screenshot: bool


class MoveMouseActionParams(TypedDict, total=False):
    """Parameters for moving the mouse pointer."""

    action: Required[Literal["move_mouse"]]
    x: Required[int]
    y: Required[int]
    return_screenshot: bool


class ScreenshotActionParams(TypedDict):
    """Parameters for capturing a browser screenshot."""

    action: Literal["screenshot"]


class ScrollActionParams(TypedDict, total=False):
    """Parameters for scrolling at a screen coordinate."""

    action: Required[Literal["scroll"]]
    x: Required[int]
    y: Required[int]
    scroll_x: Required[int]
    scroll_y: Required[int]
    return_screenshot: bool


class TypeTextActionParams(TypedDict, total=False):
    """Parameters for typing text through the computer-action API."""

    action: Required[Literal["type_text"]]
    text: Required[str]
    return_screenshot: bool


class GetClipboardTextActionParams(TypedDict, total=False):
    """Parameters for reading text from the browser clipboard."""

    action: Required[Literal["get_clipboard_text"]]
    return_screenshot: bool


class PutSelectionTextActionParams(TypedDict, total=False):
    """Parameters for replacing the current selection with text."""

    action: Required[Literal["put_selection_text"]]
    text: Required[str]
    return_screenshot: bool


class ListWindowsActionParams(TypedDict, total=False):
    """Parameters for listing browser windows."""

    action: Required[Literal["list_windows"]]
    return_screenshot: bool


ComputerActionParams: TypeAlias = Union[
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
    PutSelectionTextActionParams,
    ListWindowsActionParams,
]


__all__ = [
    "ClickActionParams",
    "ComputerActionMouseButton",
    "ComputerActionParams",
    "Coordinate",
    "DragActionParams",
    "GetClipboardTextActionParams",
    "HoldKeyActionParams",
    "ListWindowsActionParams",
    "MouseDownActionParams",
    "MouseUpActionParams",
    "MoveMouseActionParams",
    "PressKeysActionParams",
    "PutSelectionTextActionParams",
    "ScreenshotActionParams",
    "ScrollActionParams",
    "TypeTextActionParams",
]
