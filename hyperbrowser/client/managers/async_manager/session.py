from typing import List, Optional, Union, IO, overload
import warnings
from ....models.session import (
    BasicResponse,
    CaptchaEvaluationParams,
    CaptchaEvaluationResponse,
    CreateSessionParams,
    GetSessionDownloadsUrlResponse,
    GetSessionRecordingUrlResponse,
    GetSessionVideoRecordingUrlResponse,
    SessionDetail,
    SessionListParams,
    SessionListResponse,
    SessionRecording,
    UploadFileResponse,
    SessionEventLogListParams,
    SessionEventLogListResponse,
    SessionEventLog,
    UpdateSessionProfileParams,
    UpdateSessionProxyParams,
    UpdateSessionScreenParams,
    UpdateSessionSolveCaptchasParams,
    UpdateSessionSolveCaptchasResponse,
    SessionGetParams,
)

CAPTCHA_EVALUATION_REQUEST_TIMEOUT_SECONDS = 185


class SessionEventLogsManager:
    def __init__(self, client):
        self._client = client

    async def list(
        self,
        session_id: str,
        params: SessionEventLogListParams = SessionEventLogListParams(),
    ) -> List[SessionEventLog]:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{session_id}/event-logs"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionEventLogListResponse(**response.data)


class SessionManager:
    _has_warned_update_profile_params_boolean_deprecated: bool = False

    def __init__(self, client):
        self._client = client
        self.event_logs = SessionEventLogsManager(client)

    async def create(self, params: CreateSessionParams = None) -> SessionDetail:
        response = await self._client.transport.post(
            self._client._build_url("/session"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
        )
        return SessionDetail(**response.data)

    async def get(
        self, id: str, params: SessionGetParams = SessionGetParams()
    ) -> SessionDetail:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionDetail(**response.data)

    async def stop(self, id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/stop")
        )
        return BasicResponse(**response.data)

    async def evaluate_captcha(
        self,
        id: str,
        params: Optional[CaptchaEvaluationParams] = None,
    ) -> CaptchaEvaluationResponse:
        params_obj = params or CaptchaEvaluationParams()
        response = await self._client.transport.post(
            self._client._build_url(f"/session/{id}/captcha/evaluate"),
            data=params_obj.model_dump(exclude_none=True, by_alias=True),
            timeout=max(
                self._client.timeout, CAPTCHA_EVALUATION_REQUEST_TIMEOUT_SECONDS
            ),
        )
        return CaptchaEvaluationResponse(**response.data)

    async def list(
        self, params: SessionListParams = SessionListParams()
    ) -> SessionListResponse:
        response = await self._client.transport.get(
            self._client._build_url("/sessions"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionListResponse(**response.data)

    async def get_recording(self, id: str) -> List[SessionRecording]:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}/recording"), None, True
        )
        return [SessionRecording(**recording) for recording in response.data]

    async def get_recording_url(self, id: str) -> GetSessionRecordingUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}/recording-url")
        )
        return GetSessionRecordingUrlResponse(**response.data)

    async def get_video_recording_url(
        self, id: str
    ) -> GetSessionVideoRecordingUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}/video-recording-url")
        )
        return GetSessionVideoRecordingUrlResponse(**response.data)

    async def get_downloads_url(self, id: str) -> GetSessionDownloadsUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}/downloads-url")
        )
        return GetSessionDownloadsUrlResponse(**response.data)

    async def upload_file(
        self, id: str, file_input: Union[str, IO]
    ) -> UploadFileResponse:
        response = None
        if isinstance(file_input, str):
            with open(file_input, "rb") as file_obj:
                files = {"file": file_obj}
                response = await self._client.transport.post(
                    self._client._build_url(f"/session/{id}/uploads"),
                    files=files,
                )
        else:
            files = {"file": file_input}
            response = await self._client.transport.post(
                self._client._build_url(f"/session/{id}/uploads"),
                files=files,
            )

        return UploadFileResponse(**response.data)

    async def extend_session(self, id: str, duration_minutes: int) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/extend-session"),
            data={"durationMinutes": duration_minutes},
        )
        return BasicResponse(**response.data)

    @overload
    async def update_profile_params(
        self, id: str, params: UpdateSessionProfileParams
    ) -> BasicResponse: ...

    @overload
    async def update_profile_params(
        self, id: str, persist_changes: bool
    ) -> BasicResponse: ...

    async def update_profile_params(
        self,
        id: str,
        params: Union[UpdateSessionProfileParams, bool, None] = None,
        *,
        persist_changes: Optional[bool] = None,
    ) -> BasicResponse:
        params_obj: UpdateSessionProfileParams

        if isinstance(params, UpdateSessionProfileParams):
            if persist_changes is not None:
                raise TypeError(
                    "Pass either UpdateSessionProfileParams as the second argument or persist_changes=bool, not both."
                )
            params_obj = params
        elif isinstance(params, bool):
            if persist_changes is not None:
                raise TypeError(
                    "Pass either a boolean as the second argument or persist_changes=bool, not both."
                )
            self._warn_update_profile_params_boolean_deprecated()
            params_obj = UpdateSessionProfileParams(persist_changes=params)
        elif params is None:
            if persist_changes is None:
                raise TypeError(
                    "update_profile_params() requires either UpdateSessionProfileParams or persist_changes=bool."
                )
            self._warn_update_profile_params_boolean_deprecated()
            params_obj = UpdateSessionProfileParams(persist_changes=persist_changes)
        else:
            raise TypeError(
                "update_profile_params() requires either UpdateSessionProfileParams or a boolean persist_changes."
            )

        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "profile",
                "params": params_obj.model_dump(exclude_none=True, by_alias=True),
            },
        )
        return BasicResponse(**response.data)

    async def update_proxy_params(
        self,
        id: str,
        params: UpdateSessionProxyParams,
    ) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "proxy",
                "params": params.model_dump(exclude_none=True, by_alias=True),
            },
        )
        return BasicResponse(**response.data)

    async def update_screen_size(
        self,
        id: str,
        params: UpdateSessionScreenParams,
    ) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "screen",
                "params": params.model_dump(exclude_none=True, by_alias=True),
            },
        )
        return BasicResponse(**response.data)

    async def start_captcha_solving(
        self,
        id: str,
        params: Optional[UpdateSessionSolveCaptchasParams] = None,
    ) -> UpdateSessionSolveCaptchasResponse:
        params_obj = params or UpdateSessionSolveCaptchasParams()
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "solveCaptchas",
                "params": {
                    "enabled": True,
                    **params_obj.model_dump(exclude_none=True, by_alias=True),
                },
            },
        )
        return UpdateSessionSolveCaptchasResponse(**response.data)

    async def stop_captcha_solving(self, id: str) -> UpdateSessionSolveCaptchasResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "solveCaptchas",
                "params": {
                    "enabled": False,
                },
            },
        )
        return UpdateSessionSolveCaptchasResponse(**response.data)

    def _warn_update_profile_params_boolean_deprecated(self) -> None:
        if SessionManager._has_warned_update_profile_params_boolean_deprecated:
            return
        SessionManager._has_warned_update_profile_params_boolean_deprecated = True
        warnings.warn(
            "[DEPRECATED] update_profile_params(id, bool) will be removed; pass an UpdateSessionProfileParams object instead.",
            DeprecationWarning,
            stacklevel=3,
        )
