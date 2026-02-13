import os
from os import PathLike
from typing import IO, List, Optional, Union, overload
import warnings
from hyperbrowser.exceptions import HyperbrowserError
from ...file_utils import ensure_existing_file_path
from ....models.session import (
    BasicResponse,
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
    UpdateSessionProfileParams,
    SessionGetParams,
)


class SessionEventLogsManager:
    def __init__(self, client):
        self._client = client

    def list(
        self,
        session_id: str,
        params: Optional[SessionEventLogListParams] = None,
    ) -> SessionEventLogListResponse:
        params_obj = params or SessionEventLogListParams()
        response = self._client.transport.get(
            self._client._build_url(f"/session/{session_id}/event-logs"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionEventLogListResponse(**response.data)


class SessionManager:
    _has_warned_update_profile_params_boolean_deprecated: bool = False

    def __init__(self, client):
        self._client = client
        self.event_logs = SessionEventLogsManager(client)

    def create(self, params: Optional[CreateSessionParams] = None) -> SessionDetail:
        response = self._client.transport.post(
            self._client._build_url("/session"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
        )
        return SessionDetail(**response.data)

    def get(self, id: str, params: Optional[SessionGetParams] = None) -> SessionDetail:
        params_obj = params or SessionGetParams()
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionDetail(**response.data)

    def stop(self, id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/stop")
        )
        return BasicResponse(**response.data)

    def list(self, params: Optional[SessionListParams] = None) -> SessionListResponse:
        params_obj = params or SessionListParams()
        response = self._client.transport.get(
            self._client._build_url("/sessions"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
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

    def upload_file(
        self, id: str, file_input: Union[str, PathLike[str], IO]
    ) -> UploadFileResponse:
        if isinstance(file_input, (str, PathLike)):
            raw_file_path = os.fspath(file_input)
            file_path = ensure_existing_file_path(
                raw_file_path,
                missing_file_message=f"Upload file not found at path: {raw_file_path}",
                not_file_message=f"Upload file path must point to a file: {raw_file_path}",
            )
            try:
                with open(file_path, "rb") as file_obj:
                    files = {"file": file_obj}
                    response = self._client.transport.post(
                        self._client._build_url(f"/session/{id}/uploads"),
                        files=files,
                    )
            except OSError as exc:
                raise HyperbrowserError(
                    f"Failed to open upload file at path: {file_path}",
                    original_error=exc,
                ) from exc
        else:
            try:
                read_method = getattr(file_input, "read", None)
            except HyperbrowserError:
                raise
            except Exception as exc:
                raise HyperbrowserError(
                    "file_input file-like object state is invalid",
                    original_error=exc,
                ) from exc
            if callable(read_method):
                try:
                    is_closed = bool(getattr(file_input, "closed", False))
                except HyperbrowserError:
                    raise
                except Exception as exc:
                    raise HyperbrowserError(
                        "file_input file-like object state is invalid",
                        original_error=exc,
                    ) from exc
                if is_closed:
                    raise HyperbrowserError("file_input file-like object must be open")
                files = {"file": file_input}
                response = self._client.transport.post(
                    self._client._build_url(f"/session/{id}/uploads"),
                    files=files,
                )
            else:
                raise HyperbrowserError(
                    "file_input must be a file path or file-like object"
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
        self, id: str, params: UpdateSessionProfileParams
    ) -> BasicResponse: ...

    @overload
    def update_profile_params(
        self, id: str, persist_changes: bool
    ) -> BasicResponse: ...

    def update_profile_params(
        self,
        id: str,
        params: Union[UpdateSessionProfileParams, bool, None] = None,
        *,
        persist_changes: Optional[bool] = None,
    ) -> BasicResponse:
        params_obj: UpdateSessionProfileParams

        if isinstance(params, UpdateSessionProfileParams):
            if persist_changes is not None:
                raise HyperbrowserError(
                    "Pass either UpdateSessionProfileParams as the second argument or persist_changes=bool, not both."
                )
            params_obj = params
        elif isinstance(params, bool):
            if persist_changes is not None:
                raise HyperbrowserError(
                    "Pass either a boolean as the second argument or persist_changes=bool, not both."
                )
            self._warn_update_profile_params_boolean_deprecated()
            params_obj = UpdateSessionProfileParams(persist_changes=params)
        elif params is None:
            if persist_changes is None:
                raise HyperbrowserError(
                    "update_profile_params() requires either UpdateSessionProfileParams or persist_changes=bool."
                )
            self._warn_update_profile_params_boolean_deprecated()
            params_obj = UpdateSessionProfileParams(persist_changes=persist_changes)
        else:
            raise HyperbrowserError(
                "update_profile_params() requires either UpdateSessionProfileParams or a boolean persist_changes."
            )

        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={
                "type": "profile",
                "params": params_obj.model_dump(exclude_none=True, by_alias=True),
            },
        )
        return BasicResponse(**response.data)

    def _warn_update_profile_params_boolean_deprecated(self) -> None:
        if SessionManager._has_warned_update_profile_params_boolean_deprecated:
            return
        SessionManager._has_warned_update_profile_params_boolean_deprecated = True
        warnings.warn(
            "[DEPRECATED] update_profile_params(id, bool) will be removed; pass an UpdateSessionProfileParams object instead.",
            DeprecationWarning,
            stacklevel=3,
        )
