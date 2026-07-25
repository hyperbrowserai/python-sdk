import warnings
from collections.abc import Mapping
from typing import IO, List, Optional, Union, overload

from hyperbrowser.client._request import coerce_request, dump_request
from hyperbrowser.types import (
    CaptchaEvaluationParams as CaptchaEvaluationParamsDict,
    CreateSessionParams as CreateSessionParamsDict,
    SessionEventLogListParams as SessionEventLogListParamsDict,
    SessionGetParams as SessionGetParamsDict,
    SessionListParams as SessionListParamsDict,
    UpdateSessionProfileParams as UpdateSessionProfileParamsDict,
    UpdateSessionProxyParams as UpdateSessionProxyParamsDict,
    UpdateSessionScreenParams as UpdateSessionScreenParamsDict,
    UpdateSessionSolveCaptchasParams as UpdateSessionSolveCaptchasParamsDict,
)

from ....models.session import (
    BasicResponse,
    CaptchaEvaluationParams,
    CaptchaEvaluationResponse,
    CreateSessionParams,
    CreateSessionSnapshotResponse,
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

    def list(
        self,
        session_id: str,
        params: Optional[
            Union[SessionEventLogListParamsDict, SessionEventLogListParams]
        ] = None,
    ) -> SessionEventLogListResponse:
        if params is None:
            params = SessionEventLogListParams()
        response = self._client.transport.get(
            self._client._build_url(f"/session/{session_id}/event-logs"),
            params=dump_request(params, SessionEventLogListParams),
        )
        return SessionEventLogListResponse(**response.data)


class SessionManager:
    _has_warned_update_profile_params_boolean_deprecated: bool = False

    def __init__(self, client):
        self._client = client
        self.event_logs = SessionEventLogsManager(client)

    def create(
        self,
        params: Optional[Union[CreateSessionParamsDict, CreateSessionParams]] = None,
    ) -> SessionDetail:
        response = self._client.transport.post(
            self._client._build_url("/session"),
            data=({} if params is None else dump_request(params, CreateSessionParams)),
        )
        return SessionDetail(**response.data)

    def get(
        self,
        id: str,
        params: Optional[Union[SessionGetParamsDict, SessionGetParams]] = None,
    ) -> SessionDetail:
        if params is None:
            params = SessionGetParams()
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}"),
            params=dump_request(params, SessionGetParams),
        )
        return SessionDetail(**response.data)

    def stop(self, id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/stop")
        )
        return BasicResponse(**response.data)

    def create_snapshot(self, id: str) -> CreateSessionSnapshotResponse:
        response = self._client.transport.post(
            self._client._build_url(f"/session/{id}/snapshot"),
            data={},
        )
        return CreateSessionSnapshotResponse(**response.data)

    def evaluate_captcha(
        self,
        id: str,
        params: Optional[
            Union[CaptchaEvaluationParamsDict, CaptchaEvaluationParams]
        ] = None,
    ) -> CaptchaEvaluationResponse:
        params_obj = params if params is not None else CaptchaEvaluationParams()
        response = self._client.transport.post(
            self._client._build_url(f"/session/{id}/captcha/evaluate"),
            data=dump_request(params_obj, CaptchaEvaluationParams),
            timeout=max(
                self._client.timeout, CAPTCHA_EVALUATION_REQUEST_TIMEOUT_SECONDS
            ),
        )
        return CaptchaEvaluationResponse(**response.data)

    def list(
        self,
        params: Optional[Union[SessionListParamsDict, SessionListParams]] = None,
    ) -> SessionListResponse:
        if params is None:
            params = SessionListParams()
        response = self._client.transport.get(
            self._client._build_url("/sessions"),
            params=dump_request(params, SessionListParams),
        )
        return SessionListResponse(**response.data)

    def get_recording(self, id: str) -> List[SessionRecording]:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}/recording"), None, True
        )
        return [SessionRecording(**recording) for recording in response.data]

    def get_recording_url(self, id: str) -> GetSessionRecordingUrlResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}/recording-url")
        )
        return GetSessionRecordingUrlResponse(**response.data)

    def get_video_recording_url(self, id: str) -> GetSessionVideoRecordingUrlResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}/video-recording-url")
        )
        return GetSessionVideoRecordingUrlResponse(**response.data)

    def get_downloads_url(self, id: str) -> GetSessionDownloadsUrlResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}/downloads-url")
        )
        return GetSessionDownloadsUrlResponse(**response.data)

    def upload_file(self, id: str, file_input: Union[str, IO]) -> UploadFileResponse:
        response = None
        if isinstance(file_input, str):
            with open(file_input, "rb") as file_obj:
                files = {"file": file_obj}
                response = self._client.transport.post(
                    self._client._build_url(f"/session/{id}/uploads"),
                    files=files,
                )
        else:
            files = {"file": file_input}
            response = self._client.transport.post(
                self._client._build_url(f"/session/{id}/uploads"),
                files=files,
            )

        return UploadFileResponse(**response.data)

    def extend_session(self, id: str, duration_minutes: int) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/extend-session"),
            data={"durationMinutes": duration_minutes},
        )
        return BasicResponse(**response.data)

    @overload
    def update_profile_params(
        self, id: str, params: UpdateSessionProfileParamsDict
    ) -> BasicResponse: ...

    @overload
    def update_profile_params(
        self, id: str, params: UpdateSessionProfileParams
    ) -> BasicResponse: ...

    @overload
    def update_profile_params(self, id: str, params: bool) -> BasicResponse: ...

    @overload
    def update_profile_params(
        self,
        id: str,
        params: None = None,
        *,
        persist_changes: bool,
    ) -> BasicResponse: ...

    def update_profile_params(
        self,
        id: str,
        params: Union[
            UpdateSessionProfileParamsDict,
            UpdateSessionProfileParams,
            bool,
            None,
        ] = None,
        *,
        persist_changes: Optional[bool] = None,
    ) -> BasicResponse:
        params_obj: UpdateSessionProfileParams

        if isinstance(params, (UpdateSessionProfileParams, Mapping)):
            if persist_changes is not None:
                raise TypeError(
                    "Pass either UpdateSessionProfileParams as the second argument or persist_changes=bool, not both."
                )
            params_obj = coerce_request(params, UpdateSessionProfileParams)
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

        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "profile",
                "params": dump_request(params_obj, UpdateSessionProfileParams),
            },
        )
        return BasicResponse(**response.data)

    def update_proxy_params(
        self,
        id: str,
        params: Union[UpdateSessionProxyParamsDict, UpdateSessionProxyParams],
    ) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "proxy",
                "params": dump_request(params, UpdateSessionProxyParams),
            },
        )
        return BasicResponse(**response.data)

    def update_screen_size(
        self,
        id: str,
        params: Union[UpdateSessionScreenParamsDict, UpdateSessionScreenParams],
    ) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "screen",
                "params": dump_request(params, UpdateSessionScreenParams),
            },
        )
        return BasicResponse(**response.data)

    def start_captcha_solving(
        self,
        id: str,
        params: Optional[
            Union[
                UpdateSessionSolveCaptchasParamsDict,
                UpdateSessionSolveCaptchasParams,
            ]
        ] = None,
    ) -> UpdateSessionSolveCaptchasResponse:
        params_obj = (
            params if params is not None else UpdateSessionSolveCaptchasParams()
        )
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "solveCaptchas",
                "params": {
                    "enabled": True,
                    **dump_request(params_obj, UpdateSessionSolveCaptchasParams),
                },
            },
        )
        return UpdateSessionSolveCaptchasResponse(**response.data)

    def stop_captcha_solving(self, id: str) -> UpdateSessionSolveCaptchasResponse:
        response = self._client.transport.put(
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
