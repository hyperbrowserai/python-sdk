from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
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
        payload = {}
        if params is not None:
            try:
                payload = params.model_dump(exclude_none=True, by_alias=True)
            except HyperbrowserError:
                raise
            except Exception as exc:
                raise HyperbrowserError(
                    "Failed to serialize profile create params",
                    original_error=exc,
                ) from exc
            if type(payload) is not dict:
                raise HyperbrowserError("Failed to serialize profile create params")
        response = await self._client.transport.post(
            self._client._build_url("/profile"),
            data=payload,
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
        try:
            query_params = params_obj.model_dump(exclude_none=True, by_alias=True)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to serialize profile list params",
                original_error=exc,
            ) from exc
        if type(query_params) is not dict:
            raise HyperbrowserError("Failed to serialize profile list params")
        response = await self._client.transport.get(
            self._client._build_url("/profiles"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=ProfileListResponse,
            operation_name="list profiles",
        )
