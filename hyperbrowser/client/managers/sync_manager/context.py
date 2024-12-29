from hyperbrowser.models.context import ContextResponse, CreateContextResponse
from hyperbrowser.models.session import BasicResponse


class ContextManager:
    def __init__(self, client):
        self._client = client

    def create(self) -> CreateContextResponse:
        response = self._client.transport.post(
            self._client._build_url("/context"),
        )
        return CreateContextResponse(**response.data)

    def get(self, id: str) -> ContextResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/context/{id}"),
        )
        return ContextResponse(**response.data)

    def delete(self, id: str) -> BasicResponse:
        response = self._client.transport.delete(
            self._client._build_url(f"/context/{id}"),
        )
        return BasicResponse(**response.data)
