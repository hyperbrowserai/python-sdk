from collections.abc import Mapping
from typing import Union, List, Optional

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
    ComputerAction.SCROLL.value: ScrollActionParams,
    ComputerAction.TYPE_TEXT.value: TypeTextActionParams,
    ComputerAction.GET_CLIPBOARD_TEXT.value: GetClipboardTextActionParams,
    ComputerAction.PUT_SELECTION_TEXT.value: PutSelectionTextActionParams,
    ComputerAction.LIST_WINDOWS.value: ListWindowsActionParams,
}


def _action_param_model(params):
    for model in _ACTION_PARAM_MODELS.values():
        if isinstance(params, model):
            return model

    if isinstance(params, Mapping):
        action = params.get("action")
        if isinstance(action, ComputerAction):
            action = action.value
        model = _ACTION_PARAM_MODELS.get(action)
        if model is not None:
            return model

    raise TypeError("params must be a computer action params instance or mapping")


class ComputerActionManager:
    def __init__(self, client):
        self._client = client

    async def _execute_request(
        self,
        session: Union[SessionDetail, str],
        params: Union[ComputerActionParamsDict, ComputerActionParams],
    ) -> ComputerActionResponse:
        if isinstance(session, str):
            session = await self._client.sessions.get(session)

        if not session.computer_action_endpoint:
            raise ValueError("Computer action endpoint not available for this session")

        payload = dump_request(
            params,
            _action_param_model(params),
            name="params",
        )

        response = await self._client.transport.post(
            session.computer_action_endpoint,
            data=payload,
        )
        return ComputerActionResponse(**response.data)

    async def click(
        self,
        session: Union[SessionDetail, str],
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: ComputerActionMouseButton = "left",
        num_clicks: int = 1,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = ClickActionParams(
            x=x,
            y=y,
            button=button,
            num_clicks=num_clicks,
            return_screenshot=return_screenshot,
        )
        return await self._execute_request(session, params)

    async def type_text(
        self,
        session: Union[SessionDetail, str],
        text: str,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = TypeTextActionParams(text=text, return_screenshot=return_screenshot)
        return await self._execute_request(session, params)

    async def screenshot(
        self,
        session: Union[SessionDetail, str],
    ) -> ComputerActionResponse:
        params = ScreenshotActionParams()
        return await self._execute_request(session, params)

    async def press_keys(
        self,
        session: Union[SessionDetail, str],
        keys: List[str],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = PressKeysActionParams(keys=keys, return_screenshot=return_screenshot)
        return await self._execute_request(session, params)

    async def hold_key(
        self,
        session: Union[SessionDetail, str],
        key: str,
        duration: int,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = HoldKeyActionParams(
            key=key, duration=duration, return_screenshot=return_screenshot
        )
        return await self._execute_request(session, params)

    async def mouse_down(
        self,
        session: Union[SessionDetail, str],
        button: ComputerActionMouseButton = "left",
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = MouseDownActionParams(
            button=button, return_screenshot=return_screenshot
        )
        return await self._execute_request(session, params)

    async def mouse_up(
        self,
        session: Union[SessionDetail, str],
        button: ComputerActionMouseButton = "left",
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = MouseUpActionParams(button=button, return_screenshot=return_screenshot)
        return await self._execute_request(session, params)

    async def drag(
        self,
        session: Union[SessionDetail, str],
        path: List[Union[CoordinateDict, Coordinate]],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = DragActionParams(
            path=[
                coerce_request(coordinate, Coordinate, name="coordinate")
                for coordinate in path
            ],
            return_screenshot=return_screenshot,
        )
        return await self._execute_request(session, params)

    async def move_mouse(
        self,
        session: Union[SessionDetail, str],
        x: int,
        y: int,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = MoveMouseActionParams(x=x, y=y, return_screenshot=return_screenshot)
        return await self._execute_request(session, params)

    async def scroll(
        self,
        session: Union[SessionDetail, str],
        x: int,
        y: int,
        scroll_x: int,
        scroll_y: int,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = ScrollActionParams(
            x=x,
            y=y,
            scroll_x=scroll_x,
            scroll_y=scroll_y,
            return_screenshot=return_screenshot,
        )
        return await self._execute_request(session, params)

    async def get_clipboard_text(
        self,
        session: Union[SessionDetail, str],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = GetClipboardTextActionParams(return_screenshot=return_screenshot)
        return await self._execute_request(session, params)

    async def put_selection_text(
        self,
        session: Union[SessionDetail, str],
        text: str,
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = PutSelectionTextActionParams(
            text=text, return_screenshot=return_screenshot
        )
        return await self._execute_request(session, params)

    async def list_windows(
        self,
        session: Union[SessionDetail, str],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = ListWindowsActionParams(return_screenshot=return_screenshot)
        return await self._execute_request(session, params)
