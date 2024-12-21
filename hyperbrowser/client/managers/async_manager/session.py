from typing import Optional
from ....models.session import (
    BasicResponse,
    CreateSessionParams,
    SessionDetail,
    SessionListParams,
    SessionListResponse,
)


class SessionManager:
    def __init__(self, client):
        self._client = client

    async def create(self, params: CreateSessionParams) -> SessionDetail:
        response = await self._client.transport.post(
            self._client._build_url("/session"),
            data=params.model_dump(exclude_none=True, by_alias=True),
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
            self._client._build_url("/sessions"), params=params.__dict__
        )
        return SessionListResponse(**response.data)