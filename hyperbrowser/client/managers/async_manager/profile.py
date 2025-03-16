from hyperbrowser.models.profile import (
    CreateProfileResponse,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse


class ProfileManager:
    def __init__(self, client):
        self._client = client

    async def create(self) -> CreateProfileResponse:
        response = await self._client.transport.post(
            self._client._build_url("/profile"),
        )
        return CreateProfileResponse(**response.data)

    async def get(self, id: str) -> ProfileResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/profile/{id}"),
        )
        return ProfileResponse(**response.data)

    async def delete(self, id: str) -> BasicResponse:
        response = await self._client.transport.delete(
            self._client._build_url(f"/profile/{id}"),
        )
        return BasicResponse(**response.data)

    async def list(
        self, params: ProfileListParams = ProfileListParams()
    ) -> ProfileListResponse:
        response = await self._client.transport.get(
            self._client._build_url("/profiles"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return ProfileListResponse(**response.data)
