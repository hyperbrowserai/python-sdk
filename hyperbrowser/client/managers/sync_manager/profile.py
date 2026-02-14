from typing import Optional

from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse
from ..serialization_utils import serialize_model_dump_to_dict
from ..response_utils import parse_response_model


class ProfileManager:
    def __init__(self, client):
        self._client = client

    def create(
        self, params: Optional[CreateProfileParams] = None
    ) -> CreateProfileResponse:
        payload = {}
        if params is not None:
            payload = serialize_model_dump_to_dict(
                params,
                error_message="Failed to serialize profile create params",
            )
        response = self._client.transport.post(
            self._client._build_url("/profile"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=CreateProfileResponse,
            operation_name="create profile",
        )

    def get(self, id: str) -> ProfileResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/profile/{id}"),
        )
        return parse_response_model(
            response.data,
            model=ProfileResponse,
            operation_name="get profile",
        )

    def delete(self, id: str) -> BasicResponse:
        response = self._client.transport.delete(
            self._client._build_url(f"/profile/{id}"),
        )
        return parse_response_model(
            response.data,
            model=BasicResponse,
            operation_name="delete profile",
        )

    def list(self, params: Optional[ProfileListParams] = None) -> ProfileListResponse:
        params_obj = params or ProfileListParams()
        query_params = serialize_model_dump_to_dict(
            params_obj,
            error_message="Failed to serialize profile list params",
        )
        response = self._client.transport.get(
            self._client._build_url("/profiles"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=ProfileListResponse,
            operation_name="list profiles",
        )
