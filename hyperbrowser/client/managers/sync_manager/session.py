from os import PathLike
from typing import IO, List, Optional, Union, overload
import warnings
from ..serialization_utils import (
    serialize_model_dump_or_default,
    serialize_model_dump_to_dict,
    serialize_optional_model_dump_to_dict,
)
from ..session_profile_update_utils import resolve_update_profile_params
from ..session_request_utils import (
    get_session_model,
    get_session_recordings,
    post_session_model,
    put_session_model,
)
from ..session_upload_utils import open_upload_files_from_input
from ..session_operation_metadata import SESSION_OPERATION_METADATA
from ..session_route_constants import (
    SESSION_DOWNLOADS_URL_ROUTE_SUFFIX,
    SESSION_EVENT_LOGS_ROUTE_SUFFIX,
    SESSION_EXTEND_ROUTE_SUFFIX,
    SESSION_RECORDING_ROUTE_SUFFIX,
    SESSION_RECORDING_URL_ROUTE_SUFFIX,
    SESSION_ROUTE_PREFIX,
    SESSION_STOP_ROUTE_SUFFIX,
    SESSION_UPDATE_ROUTE_SUFFIX,
    SESSION_UPLOADS_ROUTE_SUFFIX,
    SESSION_VIDEO_RECORDING_URL_ROUTE_SUFFIX,
    SESSIONS_ROUTE_PATH,
)
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
    _OPERATION_METADATA = SESSION_OPERATION_METADATA
    _ROUTE_PREFIX = SESSION_ROUTE_PREFIX

    def __init__(self, client):
        self._client = client

    def list(
        self,
        session_id: str,
        params: Optional[SessionEventLogListParams] = None,
    ) -> SessionEventLogListResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=SessionEventLogListParams,
            error_message="Failed to serialize session event log params",
        )
        return get_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{session_id}{SESSION_EVENT_LOGS_ROUTE_SUFFIX}",
            params=query_params,
            model=SessionEventLogListResponse,
            operation_name=self._OPERATION_METADATA.event_logs_operation_name,
        )


class SessionManager:
    _has_warned_update_profile_params_boolean_deprecated: bool = False
    _OPERATION_METADATA = SESSION_OPERATION_METADATA
    _ROUTE_PREFIX = SESSION_ROUTE_PREFIX
    _LIST_ROUTE_PATH = SESSIONS_ROUTE_PATH

    def __init__(self, client):
        self._client = client
        self.event_logs = SessionEventLogsManager(client)

    def create(self, params: Optional[CreateSessionParams] = None) -> SessionDetail:
        payload = serialize_optional_model_dump_to_dict(
            params,
            error_message="Failed to serialize session create params",
        )
        return post_session_model(
            client=self._client,
            route_path=self._ROUTE_PREFIX,
            data=payload,
            model=SessionDetail,
            operation_name=self._OPERATION_METADATA.detail_operation_name,
        )

    def get(self, id: str, params: Optional[SessionGetParams] = None) -> SessionDetail:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=SessionGetParams,
            error_message="Failed to serialize session get params",
        )
        return get_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}",
            params=query_params,
            model=SessionDetail,
            operation_name=self._OPERATION_METADATA.detail_operation_name,
        )

    def stop(self, id: str) -> BasicResponse:
        return put_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_STOP_ROUTE_SUFFIX}",
            model=BasicResponse,
            operation_name=self._OPERATION_METADATA.stop_operation_name,
        )

    def list(self, params: Optional[SessionListParams] = None) -> SessionListResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=SessionListParams,
            error_message="Failed to serialize session list params",
        )
        return get_session_model(
            client=self._client,
            route_path=self._LIST_ROUTE_PATH,
            params=query_params,
            model=SessionListResponse,
            operation_name=self._OPERATION_METADATA.list_operation_name,
        )

    def get_recording(self, id: str) -> List[SessionRecording]:
        return get_session_recordings(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_RECORDING_ROUTE_SUFFIX}",
        )

    def get_recording_url(self, id: str) -> GetSessionRecordingUrlResponse:
        return get_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_RECORDING_URL_ROUTE_SUFFIX}",
            model=GetSessionRecordingUrlResponse,
            operation_name=self._OPERATION_METADATA.recording_url_operation_name,
        )

    def get_video_recording_url(self, id: str) -> GetSessionVideoRecordingUrlResponse:
        return get_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_VIDEO_RECORDING_URL_ROUTE_SUFFIX}",
            model=GetSessionVideoRecordingUrlResponse,
            operation_name=self._OPERATION_METADATA.video_recording_url_operation_name,
        )

    def get_downloads_url(self, id: str) -> GetSessionDownloadsUrlResponse:
        return get_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_DOWNLOADS_URL_ROUTE_SUFFIX}",
            model=GetSessionDownloadsUrlResponse,
            operation_name=self._OPERATION_METADATA.downloads_url_operation_name,
        )

    def upload_file(
        self, id: str, file_input: Union[str, PathLike[str], IO]
    ) -> UploadFileResponse:
        with open_upload_files_from_input(file_input) as files:
            return post_session_model(
                client=self._client,
                route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_UPLOADS_ROUTE_SUFFIX}",
                files=files,
                model=UploadFileResponse,
                operation_name=self._OPERATION_METADATA.upload_file_operation_name,
            )

    def extend_session(self, id: str, duration_minutes: int) -> BasicResponse:
        return put_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_EXTEND_ROUTE_SUFFIX}",
            data={"durationMinutes": duration_minutes},
            model=BasicResponse,
            operation_name=self._OPERATION_METADATA.extend_operation_name,
        )

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
        params_obj = resolve_update_profile_params(
            params,
            persist_changes=persist_changes,
            on_deprecated_bool_usage=self._warn_update_profile_params_boolean_deprecated,
        )

        serialized_params = serialize_model_dump_to_dict(
            params_obj,
            error_message="Failed to serialize update_profile_params payload",
        )

        return put_session_model(
            client=self._client,
            route_path=f"{self._ROUTE_PREFIX}/{id}{SESSION_UPDATE_ROUTE_SUFFIX}",
            data={
                "type": "profile",
                "params": serialized_params,
            },
            model=BasicResponse,
            operation_name=self._OPERATION_METADATA.update_profile_operation_name,
        )

    def _warn_update_profile_params_boolean_deprecated(self) -> None:
        if SessionManager._has_warned_update_profile_params_boolean_deprecated:
            return
        SessionManager._has_warned_update_profile_params_boolean_deprecated = True
        warnings.warn(
            "[DEPRECATED] update_profile_params(id, bool) will be removed; pass an UpdateSessionProfileParams object instead.",
            DeprecationWarning,
            stacklevel=3,
        )
