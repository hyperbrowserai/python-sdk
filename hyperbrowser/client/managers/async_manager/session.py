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

    async def get(self, id: str) -> SessionDetail:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}")
        )
        return SessionDetail(**response.data)

    async def stop(self, id: str) -> BasicResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/session/{id}/stop")
        )
        return BasicResponse(**response.data)

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

    async def get_downloads_url(self, id: str) -> GetSessionDownloadsUrlResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/session/{id}/downloads-url")
        )
        return GetSessionDownloadsUrlResponse(**response.data)
