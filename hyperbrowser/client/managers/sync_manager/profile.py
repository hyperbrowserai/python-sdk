from typing import Optional

from hyperbrowser.models.profile import (
    CreateProfileParams,
    CreateProfileResponse,
    ProfileListParams,
    ProfileListResponse,
    ProfileResponse,
)
from hyperbrowser.models.session import BasicResponse
from ..profile_operation_metadata import PROFILE_OPERATION_METADATA
from ..profile_request_utils import (
    create_profile_resource,
    delete_profile_resource,
    get_profile_resource,
    list_profile_resources,
)
from ..profile_route_constants import PROFILE_ROUTE_PREFIX, PROFILES_ROUTE_PATH
from ..serialization_utils import (
    serialize_model_dump_or_default,
    serialize_optional_model_dump_to_dict,
)


class ProfileManager:
    _OPERATION_METADATA = PROFILE_OPERATION_METADATA
    _ROUTE_PREFIX = PROFILE_ROUTE_PREFIX
    _LIST_ROUTE_PATH = PROFILES_ROUTE_PATH

    def __init__(self, client):
        self._client = client

    def create(
        self, params: Optional[CreateProfileParams] = None
    ) -> CreateProfileResponse:
        payload = serialize_optional_model_dump_to_dict(
            params,
            error_message="Failed to serialize profile create params",
        )
        return create_profile_resource(
            client=self._client,
            route_prefix=self._ROUTE_PREFIX,
            payload=payload,
            model=CreateProfileResponse,
            operation_name=self._OPERATION_METADATA.create_operation_name,
        )

    def get(self, id: str) -> ProfileResponse:
        return get_profile_resource(
            client=self._client,
            profile_id=id,
            model=ProfileResponse,
            operation_name=self._OPERATION_METADATA.get_operation_name,
        )

    def delete(self, id: str) -> BasicResponse:
        return delete_profile_resource(
            client=self._client,
            profile_id=id,
            model=BasicResponse,
            operation_name=self._OPERATION_METADATA.delete_operation_name,
        )

    def list(self, params: Optional[ProfileListParams] = None) -> ProfileListResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=ProfileListParams,
            error_message="Failed to serialize profile list params",
        )
        return list_profile_resources(
            client=self._client,
            list_route_path=self._LIST_ROUTE_PATH,
            params=query_params,
            model=ProfileListResponse,
            operation_name=self._OPERATION_METADATA.list_operation_name,
        )
