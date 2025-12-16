from typing import List, Union, IO
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
    SessionEventLog,
)


class SessionEventLogsManager:
    def __init__(self, client):
        self._client = client

    def list(
        self,
        session_id: str,
        params: SessionEventLogListParams = SessionEventLogListParams(),
    ) -> SessionEventLogListResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{session_id}/event-logs"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SessionEventLogListResponse(**response.data)


class SessionManager:
    def __init__(self, client):
        self._client = client
        self.event_logs = SessionEventLogsManager(client)

    def create(self, params: CreateSessionParams = None) -> SessionDetail:
        response = self._client.transport.post(
            self._client._build_url("/session"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
        )
        return SessionDetail(**response.data)

    def get(self, id: str) -> SessionDetail:
        response = self._client.transport.get(self._client._build_url(f"/session/{id}"))
        return SessionDetail(**response.data)

    def stop(self, id: str) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/stop")
        )
        return BasicResponse(**response.data)

    def list(
        self, params: SessionListParams = SessionListParams()
    ) -> SessionListResponse:
        response = self._client.transport.get(
            self._client._build_url("/sessions"),
            params=params.model_dump(exclude_none=True, by_alias=True),
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

    def update_profile_params(self, id: str, persist_changes: bool) -> BasicResponse:
        response = self._client.transport.put(
            self._client._build_url(f"/session/{id}/update"),
            data={"type": "profile", "params": {"persistChanges": persist_changes}},
        )
        return BasicResponse(**response.data)
