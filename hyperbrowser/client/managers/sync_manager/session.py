from typing import List
from ....models.session import (
    BasicResponse,
    CreateSessionParams,
    GetSessionDownloadsUrlResponse,
    GetSessionRecordingUrlResponse,
    SessionDetail,
    SessionListParams,
    SessionListResponse,
    SessionRecording,
)


class SessionManager:
    def __init__(self, client):
        self._client = client

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

    def get_downloads_url(self, id: str) -> GetSessionDownloadsUrlResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}/downloads-url")
        )
        return GetSessionDownloadsUrlResponse(**response.data)
