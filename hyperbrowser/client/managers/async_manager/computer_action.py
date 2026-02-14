from typing import Union, List, Optional
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_string, is_string_subclass_instance
from ..computer_action_operation_metadata import COMPUTER_ACTION_OPERATION_METADATA
from ..computer_action_request_utils import execute_computer_action_request_async
from ..computer_action_utils import normalize_computer_action_endpoint
from ..computer_action_payload_utils import build_computer_action_payload
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
    PutSelectionTextActionParams,
)


class ComputerActionManager:
    _OPERATION_METADATA = COMPUTER_ACTION_OPERATION_METADATA

    def __init__(self, client):
        self._client = client

    async def _execute_request(
        self, session: Union[SessionDetail, str], params: ComputerActionParams
    ) -> ComputerActionResponse:
        if is_plain_string(session):
            session = await self._client.sessions.get(session)
        elif is_string_subclass_instance(session):
            raise HyperbrowserError(
                "session must be a plain string session ID or SessionDetail"
            )

        normalized_computer_action_endpoint = normalize_computer_action_endpoint(
            session
        )

        payload = build_computer_action_payload(params)

        return await execute_computer_action_request_async(
            client=self._client,
            endpoint=normalized_computer_action_endpoint,
            payload=payload,
            operation_name=self._OPERATION_METADATA.operation_name,
        )

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
