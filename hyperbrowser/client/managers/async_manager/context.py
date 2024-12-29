from hyperbrowser.models.context import ContextResponse, CreateContextResponse
from hyperbrowser.models.session import BasicResponse


class ContextManager:
    def __init__(self, client):
        self._client = client

    async def create(self) -> CreateContextResponse:
        response = await self._client.transport.post(
            self._client._build_url("/context"),
        )
        return CreateContextResponse(**response.data)

    async def get(self, id: str) -> ContextResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/context/{id}"),
        )
        return ContextResponse(**response.data)

    async def delete(self, id: str) -> BasicResponse:
        response = await self._client.transport.delete(
            self._client._build_url(f"/context/{id}"),
        )
        return BasicResponse(**response.data)
