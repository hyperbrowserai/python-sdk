from typing import List
from ....models.session import (
    BasicResponse,
    CreateSessionParams,
    SessionDetail,
    SessionListParams,
    SessionListResponse,
    SessionRecording,
)


class SessionManager:
    def __init__(self, client):
        self._client = client

    def create(self, params: CreateSessionParams) -> SessionDetail:
        response = self._client.transport.post(
            self._client._build_url("/session"),
            data=params.model_dump(exclude_none=True, by_alias=True),
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
            self._client._build_url("/sessions"), params=params.__dict__
        )
        return SessionListResponse(**response.data)

    def get_recording(self, id: str) -> List[SessionRecording]:
        response = self._client.transport.get(
            self._client._build_url(f"/session/{id}/recording")
        )
        return [SessionRecording(**recording) for recording in response.data]
