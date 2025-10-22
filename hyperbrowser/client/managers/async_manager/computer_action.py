from pydantic import BaseModel
from typing import Union, List, Optional
from hyperbrowser.models import (
    SessionDetail,
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
)


class ComputerActionManager:
    def __init__(self, client):
        self._client = client

    async def _execute_request(
        self, session: Union[SessionDetail, str], params: ComputerActionParams
    ) -> ComputerActionResponse:
        if isinstance(session, str):
            session = await self._client.sessions.get(session)

        if not session.computer_action_endpoint:
            raise ValueError("Computer action endpoint not available for this session")

        if isinstance(params, BaseModel):
            payload = params.model_dump(by_alias=True, exclude_none=True)
        else:
            payload = params

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
        path: List[Coordinate],
        return_screenshot: bool = False,
    ) -> ComputerActionResponse:
        params = DragActionParams(path=path, return_screenshot=return_screenshot)
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
