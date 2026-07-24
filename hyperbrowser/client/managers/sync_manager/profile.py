from typing import Optional, Union

from hyperbrowser.models.params import (
    coerce_to_model,
    CreateProfileParamsDict,
    ForkProfileParamsDict,
    ProfileListParamsDict,
)
from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ForkProfileParams,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse


class ProfileManager:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        params: Optional[Union[CreateProfileParams, CreateProfileParamsDict]] = None,
    ) -> CreateProfileResponse:
        response = self._client.transport.post(
            self._client._build_url("/profile"),
            data=(
                {}
                if params is None
                else coerce_to_model(CreateProfileParams, params).model_dump(
                    exclude_none=True, by_alias=True
                )
            ),
        )
        return CreateProfileResponse(**response.data)

    def fork(
        self,
        id: str,
        params: Optional[Union[ForkProfileParams, ForkProfileParamsDict]] = None,
    ) -> CreateProfileResponse:
        response = self._client.transport.post(
            self._client._build_url(f"/profile/{id}/fork"),
            data=(
                {}
                if params is None
                else coerce_to_model(ForkProfileParams, params).model_dump(
                    exclude_none=True, by_alias=True
                )
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

    def list(
        self,
        params: Union[ProfileListParams, ProfileListParamsDict] = ProfileListParams(),
    ) -> ProfileListResponse:
        params = coerce_to_model(ProfileListParams, params)
        response = self._client.transport.get(
            self._client._build_url("/profiles"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return ProfileListResponse(**response.data)
