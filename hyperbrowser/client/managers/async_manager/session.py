from os import PathLike
from typing import IO, List, Optional, Union, overload
import warnings
from ..serialization_utils import (
    serialize_model_dump_or_default,
    serialize_model_dump_to_dict,
    serialize_optional_model_dump_to_dict,
)
from ..session_profile_update_utils import resolve_update_profile_params
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
from ..session_utils import (
    parse_session_recordings_response_data,
    parse_session_response_model,
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

    async def list(
        self,
        session_id: str,
        params: Optional[SessionEventLogListParams] = None,
    ) -> SessionEventLogListResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=SessionEventLogListParams,
            error_message="Failed to serialize session event log params",
        )
        response = await self._client.transport.get(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{session_id}{SESSION_EVENT_LOGS_ROUTE_SUFFIX}"
            ),
            params=query_params,
        )
        return parse_session_response_model(
            response.data,
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

    async def create(
        self, params: Optional[CreateSessionParams] = None
    ) -> SessionDetail:
        payload = serialize_optional_model_dump_to_dict(
            params,
            error_message="Failed to serialize session create params",
        )
        response = await self._client.transport.post(
            self._client._build_url(self._ROUTE_PREFIX),
            data=payload,
        )
        return parse_session_response_model(
            response.data,
            model=SessionDetail,
            operation_name=self._OPERATION_METADATA.detail_operation_name,
        )

    async def get(
        self, id: str, params: Optional[SessionGetParams] = None
    ) -> SessionDetail:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=SessionGetParams,
            error_message="Failed to serialize session get params",
        )
        response = await self._client.transport.get(
            self._client._build_url(f"{self._ROUTE_PREFIX}/{id}"),
            params=query_params,
        )
        return parse_session_response_model(
            response.data,
            model=SessionDetail,
            operation_name=self._OPERATION_METADATA.detail_operation_name,
        )

    async def stop(self, id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"{self._ROUTE_PREFIX}/{id}{SESSION_STOP_ROUTE_SUFFIX}")
        )
        return parse_session_response_model(
            response.data,
            model=BasicResponse,
            operation_name=self._OPERATION_METADATA.stop_operation_name,
        )

    async def list(
        self, params: Optional[SessionListParams] = None
    ) -> SessionListResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=SessionListParams,
            error_message="Failed to serialize session list params",
        )
        response = await self._client.transport.get(
            self._client._build_url(self._LIST_ROUTE_PATH),
            params=query_params,
        )
        return parse_session_response_model(
            response.data,
            model=SessionListResponse,
            operation_name=self._OPERATION_METADATA.list_operation_name,
        )

    async def get_recording(self, id: str) -> List[SessionRecording]:
        response = await self._client.transport.get(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{id}{SESSION_RECORDING_ROUTE_SUFFIX}"
            ),
            None,
            True,
        )
        return parse_session_recordings_response_data(response.data)

    async def get_recording_url(self, id: str) -> GetSessionRecordingUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{id}{SESSION_RECORDING_URL_ROUTE_SUFFIX}"
            )
        )
        return parse_session_response_model(
            response.data,
            model=GetSessionRecordingUrlResponse,
            operation_name=self._OPERATION_METADATA.recording_url_operation_name,
        )

    async def get_video_recording_url(
        self, id: str
    ) -> GetSessionVideoRecordingUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{id}{SESSION_VIDEO_RECORDING_URL_ROUTE_SUFFIX}"
            )
        )
        return parse_session_response_model(
            response.data,
            model=GetSessionVideoRecordingUrlResponse,
            operation_name=self._OPERATION_METADATA.video_recording_url_operation_name,
        )

    async def get_downloads_url(self, id: str) -> GetSessionDownloadsUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{id}{SESSION_DOWNLOADS_URL_ROUTE_SUFFIX}"
            )
        )
        return parse_session_response_model(
            response.data,
            model=GetSessionDownloadsUrlResponse,
            operation_name=self._OPERATION_METADATA.downloads_url_operation_name,
        )

    async def upload_file(
        self, id: str, file_input: Union[str, PathLike[str], IO]
    ) -> UploadFileResponse:
        with open_upload_files_from_input(file_input) as files:
            response = await self._client.transport.post(
                self._client._build_url(
                    f"{self._ROUTE_PREFIX}/{id}{SESSION_UPLOADS_ROUTE_SUFFIX}"
                ),
                files=files,
            )

        return parse_session_response_model(
            response.data,
            model=UploadFileResponse,
            operation_name=self._OPERATION_METADATA.upload_file_operation_name,
        )

    async def extend_session(self, id: str, duration_minutes: int) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{id}{SESSION_EXTEND_ROUTE_SUFFIX}"
            ),
            data={"durationMinutes": duration_minutes},
        )
        return parse_session_response_model(
            response.data,
            model=BasicResponse,
            operation_name=self._OPERATION_METADATA.extend_operation_name,
        )

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
        params_obj = resolve_update_profile_params(
            params,
            persist_changes=persist_changes,
            on_deprecated_bool_usage=self._warn_update_profile_params_boolean_deprecated,
        )

        serialized_params = serialize_model_dump_to_dict(
            params_obj,
            error_message="Failed to serialize update_profile_params payload",
        )

        response = await self._client.transport.put(
            self._client._build_url(
                f"{self._ROUTE_PREFIX}/{id}{SESSION_UPDATE_ROUTE_SUFFIX}"
            ),
            data={
                "type": "profile",
                "params": serialized_params,
            },
        )
        return parse_session_response_model(
            response.data,
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
