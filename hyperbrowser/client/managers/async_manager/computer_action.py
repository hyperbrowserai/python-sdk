from pydantic import BaseModel
from typing import Union, List, Optional
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_string_subclass_instance
from ..response_utils import parse_response_model
from ..serialization_utils import serialize_model_dump_to_dict
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
    def __init__(self, client):
        self._client = client

    async def _execute_request(
        self, session: Union[SessionDetail, str], params: ComputerActionParams
    ) -> ComputerActionResponse:
        if type(session) is str:
            session = await self._client.sessions.get(session)
        elif is_string_subclass_instance(session):
            raise HyperbrowserError(
                "session must be a plain string session ID or SessionDetail"
            )

        try:
            computer_action_endpoint = session.computer_action_endpoint
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "session must include computer_action_endpoint",
                original_error=exc,
            ) from exc

        if computer_action_endpoint is None:
            raise HyperbrowserError(
                "Computer action endpoint not available for this session"
            )
        if type(computer_action_endpoint) is not str:
            raise HyperbrowserError("session computer_action_endpoint must be a string")
        try:
            normalized_computer_action_endpoint = computer_action_endpoint.strip()
            if type(normalized_computer_action_endpoint) is not str:
                raise TypeError("normalized computer_action_endpoint must be a string")
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize session computer_action_endpoint",
                original_error=exc,
            ) from exc

        if not normalized_computer_action_endpoint:
            raise HyperbrowserError(
                "Computer action endpoint not available for this session"
            )
        if normalized_computer_action_endpoint != computer_action_endpoint:
            raise HyperbrowserError(
                "session computer_action_endpoint must not contain leading or trailing whitespace"
            )
        try:
            contains_control_character = any(
                ord(character) < 32 or ord(character) == 127
                for character in normalized_computer_action_endpoint
            )
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to validate session computer_action_endpoint characters",
                original_error=exc,
            ) from exc
        if contains_control_character:
            raise HyperbrowserError(
                "session computer_action_endpoint must not contain control characters"
            )

        if isinstance(params, BaseModel):
            payload = serialize_model_dump_to_dict(
                params,
                error_message="Failed to serialize computer action params",
                by_alias=True,
                exclude_none=True,
            )
        else:
            payload = params

        response = await self._client.transport.post(
            normalized_computer_action_endpoint,
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=ComputerActionResponse,
            operation_name="computer action",
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
