from collections.abc import Mapping
from typing import Any, Dict, Union, List, Optional, Type, TypeVar

from hyperbrowser.client._request import coerce_request, dump_request
from hyperbrowser.models import (
    SessionDetail,
    ComputerAction,
    ComputerActionParams,
    ComputerActionResponse,
    ClickActionParams,
    DragActionParams,
    PressKeysActionParams,
    MoveMouseActionParams,
    ScreenshotActionParams,
    CursorPositionActionParams,
    CursorPositionActionResponse,
    ScrollAtCursorActionParams,
    ScrollActionParams,
    TypeTextActionParams,
    Coordinate,
    HoldKeyActionParams,
    MouseDownActionParams,
    MouseUpActionParams,
    ComputerActionMouseButton,
    GetClipboardTextActionParams,
    PutSelectionTextActionParams,
    ListWindowsActionParams,
)
from hyperbrowser.types import (
    ComputerActionParams as ComputerActionParamsDict,
    Coordinate as CoordinateDict,
)


_ACTION_PARAM_MODELS = {
    ComputerAction.CLICK.value: ClickActionParams,
    ComputerAction.DRAG.value: DragActionParams,
    ComputerAction.HOLD_KEY.value: HoldKeyActionParams,
    ComputerAction.MOUSE_DOWN.value: MouseDownActionParams,
    ComputerAction.MOUSE_UP.value: MouseUpActionParams,
    ComputerAction.MOVE_MOUSE.value: MoveMouseActionParams,
    ComputerAction.PRESS_KEYS.value: PressKeysActionParams,
    ComputerAction.SCREENSHOT.value: ScreenshotActionParams,
    ComputerAction.CURSOR_POSITION.value: CursorPositionActionParams,
    ComputerAction.SCROLL.value: ScrollActionParams,
    ComputerAction.TYPE_TEXT.value: TypeTextActionParams,
    ComputerAction.GET_CLIPBOARD_TEXT.value: GetClipboardTextActionParams,
    ComputerAction.PUT_SELECTION_TEXT.value: PutSelectionTextActionParams,
    ComputerAction.LIST_WINDOWS.value: ListWindowsActionParams,
}

_ResponseModel = TypeVar(
    "_ResponseModel", ComputerActionResponse, CursorPositionActionResponse
)


def _action_param_model(params):
    if isinstance(params, ScrollAtCursorActionParams):
        return ScrollAtCursorActionParams

    for model in _ACTION_PARAM_MODELS.values():
        if isinstance(params, model):
            return model

    if isinstance(params, Mapping):
        action = params.get("action")
        if isinstance(action, ComputerAction):
            action = action.value
        model = _ACTION_PARAM_MODELS.get(action)
        if model is ScrollActionParams and "x" not in params and "y" not in params:
            return ScrollAtCursorActionParams
        if model is not None:
            return model

    raise TypeError("params must be a computer action params instance or mapping")


class ComputerActionManager:
    def __init__(self, client):
        self._client = client

    def _execute_request(
        self,
        session: Union[SessionDetail, str],
        params: Union[ComputerActionParamsDict, ComputerActionParams],
    ) -> ComputerActionResponse:
        payload = dump_request(params, _action_param_model(params), name="params")
        return self._post_request(session, payload, ComputerActionResponse)

    def _post_request(
        self,
        session: Union[SessionDetail, str],
        payload: Dict[str, Any],
        response_model: Type[_ResponseModel],
    ) -> _ResponseModel:
        if isinstance(session, str):
            session = self._client.sessions.get(session)

        if not session.computer_action_endpoint:
            raise ValueError("Computer action endpoint not available for this session")

        response = self._client.transport.post(
            session.computer_action_endpoint,
            data=payload,
        )
        return response_model(**response.data)

    def click(
        self,
        session: Union[SessionDetail, str],
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: ComputerActionMouseButton = "left",
        num_clicks: int = 1,
        return_screenshot: bool = False,
        keys: Optional[List[str]] = None,
    ) -> ComputerActionResponse:
        params = ClickActionParams(
            x=x,
            y=y,
            button=button,
            num_clicks=num_clicks,
            keys=keys,
            return_screenshot=return_screenshot,
        )
        return self._execute_request(session, params)

    def type_text(
        self,
        session: Union[SessionDetail, str],
        text: str,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = TypeTextActionParams(text=text, return_screenshot=return_screenshot)
        return self._execute_request(session, params)

    def screenshot(
        self,
        session: Union[SessionDetail, str],
    ) -> ComputerActionResponse:
        params = ScreenshotActionParams()
        return self._execute_request(session, params)

    def cursor_position(
        self,
        session: Union[SessionDetail, str],
        return_screenshot: bool = False,
    ) -> CursorPositionActionResponse:
        params = CursorPositionActionParams(return_screenshot=return_screenshot)
        payload = dump_request(params, CursorPositionActionParams, name="params")
        return self._post_request(session, payload, CursorPositionActionResponse)

    def press_keys(
        self,
        session: Union[SessionDetail, str],
        keys: List[str],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = PressKeysActionParams(keys=keys, return_screenshot=return_screenshot)
        return self._execute_request(session, params)

    def hold_key(
        self,
        session: Union[SessionDetail, str],
        key: str,
        duration: int,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = HoldKeyActionParams(
            key=key, duration=duration, return_screenshot=return_screenshot
        )
        return self._execute_request(session, params)

    def mouse_down(
        self,
        session: Union[SessionDetail, str],
        button: ComputerActionMouseButton = "left",
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = MouseDownActionParams(
            button=button, return_screenshot=return_screenshot
        )
        return self._execute_request(session, params)

    def mouse_up(
        self,
        session: Union[SessionDetail, str],
        button: ComputerActionMouseButton = "left",
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = MouseUpActionParams(button=button, return_screenshot=return_screenshot)
        return self._execute_request(session, params)

    def drag(
        self,
        session: Union[SessionDetail, str],
        path: List[Union[CoordinateDict, Coordinate]],
        return_screenshot: bool = False,
        keys: Optional[List[str]] = None,
    ) -> ComputerActionResponse:
        params = DragActionParams(
            path=[
                coerce_request(coordinate, Coordinate, name="coordinate")
                for coordinate in path
            ],
            return_screenshot=return_screenshot,
            keys=keys,
        )
        return self._execute_request(session, params)

    def move_mouse(
        self,
        session: Union[SessionDetail, str],
        x: int,
        y: int,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = MoveMouseActionParams(x=x, y=y, return_screenshot=return_screenshot)
        return self._execute_request(session, params)

    def scroll(
        self,
        session: Union[SessionDetail, str],
        x: int,
        y: int,
        scroll_x: int,
        scroll_y: int,
        return_screenshot: bool = False,
        keys: Optional[List[str]] = None,
    ) -> ComputerActionResponse:
        params = ScrollActionParams(
            x=x,
            y=y,
            scroll_x=scroll_x,
            scroll_y=scroll_y,
            keys=keys,
            return_screenshot=return_screenshot,
        )
        return self._execute_request(session, params)

    def scroll_at_cursor(
        self,
        session: Union[SessionDetail, str],
        scroll_x: int = 0,
        scroll_y: int = 0,
        return_screenshot: bool = False,
        keys: Optional[List[str]] = None,
    ) -> ComputerActionResponse:
        params = ScrollAtCursorActionParams(
            scroll_x=scroll_x,
            scroll_y=scroll_y,
            keys=keys,
            return_screenshot=return_screenshot,
        )
        return self._execute_request(session, params)

    def get_clipboard_text(
        self,
        session: Union[SessionDetail, str],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = GetClipboardTextActionParams(return_screenshot=return_screenshot)
        return self._execute_request(session, params)

    def put_selection_text(
        self,
        session: Union[SessionDetail, str],
        text: str,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = PutSelectionTextActionParams(
            text=text, return_screenshot=return_screenshot
        )
        return self._execute_request(session, params)

    def list_windows(
        self,
        session: Union[SessionDetail, str],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = ListWindowsActionParams(return_screenshot=return_screenshot)
        return self._execute_request(session, params)
