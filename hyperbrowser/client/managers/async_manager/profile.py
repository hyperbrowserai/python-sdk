from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
    UpdateProfileParams,
    BatchDeleteProfilesParams,
)
from hyperbrowser.models.session import BasicResponse


class ProfileManager:
    def __init__(self, client):
        self._client = client

    async def create(self, params: CreateProfileParams = None) -> CreateProfileResponse:
        response = await self._client.transport.post(
            self._client._build_url("/profile"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
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

    async def update(self, id: str, params: UpdateProfileParams) -> ProfileResponse:
        response = await self._client.transport.put(
            self._client._build_url(f"/profile/{id}"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return ProfileResponse(**response.data)

    async def delete_many(self, params: BatchDeleteProfilesParams) -> BasicResponse:
        response = await self._client.transport.client.request(
            "DELETE",
            self._client._build_url("/profiles"),
            json=params.model_dump(exclude_none=True, by_alias=True),
        )
        handled = await self._client.transport._handle_response(response)
        return BasicResponse(**handled.data)

    async def list(
        self, params: ProfileListParams = ProfileListParams()
    ) -> ProfileListResponse:
        response = await self._client.transport.get(
            self._client._build_url("/profiles"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return ProfileListResponse(**response.data)
