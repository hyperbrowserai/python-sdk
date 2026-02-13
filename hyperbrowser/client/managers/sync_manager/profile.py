from typing import Optional

from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse


class ProfileManager:
    def __init__(self, client):
        self._client = client

    def create(
        self, params: Optional[CreateProfileParams] = None
    ) -> CreateProfileResponse:
        response = self._client.transport.post(
            self._client._build_url("/profile"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
        )
        return CreateProfileResponse(**response.data)

    def get(self, id: str) -> ProfileResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/profile/{id}"),
        )
        return ProfileResponse(**response.data)

    def delete(self, id: str) -> BasicResponse:
        response = self._client.transport.delete(
            self._client._build_url(f"/profile/{id}"),
        )
        return BasicResponse(**response.data)

    def list(self, params: Optional[ProfileListParams] = None) -> ProfileListResponse:
        params_obj = params or ProfileListParams()
        response = self._client.transport.get(
            self._client._build_url("/profiles"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return ProfileListResponse(**response.data)
