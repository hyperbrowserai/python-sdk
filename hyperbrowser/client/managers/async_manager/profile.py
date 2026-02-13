from typing import Optional

from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse
from ..response_utils import parse_response_model


class ProfileManager:
    def __init__(self, client):
        self._client = client

    async def create(
        self, params: Optional[CreateProfileParams] = None
    ) -> CreateProfileResponse:
        response = await self._client.transport.post(
            self._client._build_url("/profile"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
        )
        return parse_response_model(
            response.data,
            model=CreateProfileResponse,
            operation_name="create profile",
        )

    async def get(self, id: str) -> ProfileResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/profile/{id}"),
        )
        return parse_response_model(
            response.data,
            model=ProfileResponse,
            operation_name="get profile",
        )

    async def delete(self, id: str) -> BasicResponse:
        response = await self._client.transport.delete(
            self._client._build_url(f"/profile/{id}"),
        )
        return parse_response_model(
            response.data,
            model=BasicResponse,
            operation_name="delete profile",
        )

    async def list(
        self, params: Optional[ProfileListParams] = None
    ) -> ProfileListResponse:
        params_obj = params or ProfileListParams()
        response = await self._client.transport.get(
            self._client._build_url("/profiles"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return parse_response_model(
            response.data,
            model=ProfileListResponse,
            operation_name="list profiles",
        )
