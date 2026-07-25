from typing import Optional, Union

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ForkProfileParams,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse
from hyperbrowser.types import (
    CreateProfileParams as CreateProfileParamsDict,
    ForkProfileParams as ForkProfileParamsDict,
    ProfileListParams as ProfileListParamsDict,
)


class ProfileManager:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        params: Optional[Union[CreateProfileParamsDict, CreateProfileParams]] = None,
    ) -> CreateProfileResponse:
        response = self._client.transport.post(
            self._client._build_url("/profile"),
            data=({} if params is None else dump_request(params, CreateProfileParams)),
        )
        return CreateProfileResponse(**response.data)

    def fork(
        self,
        id: str,
        params: Optional[Union[ForkProfileParamsDict, ForkProfileParams]] = None,
    ) -> CreateProfileResponse:
        response = self._client.transport.post(
            self._client._build_url(f"/profile/{id}/fork"),
            data=({} if params is None else dump_request(params, ForkProfileParams)),
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
        params: Optional[Union[ProfileListParamsDict, ProfileListParams]] = None,
    ) -> ProfileListResponse:
        if params is None:
            params = ProfileListParams()
        response = self._client.transport.get(
            self._client._build_url("/profiles"),
            params=dump_request(params, ProfileListParams),
        )
        return ProfileListResponse(**response.data)
