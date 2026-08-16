from typing import Optional, Union

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.volume import (
    CreateVolumeParams,
    Volume,
    VolumeDeleteResult,
    VolumeListParams,
    VolumeListResponse,
)
from hyperbrowser.types import CreateVolumeParams as CreateVolumeParamsDict
from hyperbrowser.types import VolumeListParams as VolumeListParamsDict


class VolumeManager:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        params: Union[CreateVolumeParamsDict, CreateVolumeParams],
    ) -> Volume:
        response = self._client.transport.post(
            self._client._build_url("/volume"),
            data=dump_request(params, CreateVolumeParams),
        )
        return Volume(**response.data)

    def list(
        self,
        params: Optional[Union[VolumeListParamsDict, VolumeListParams]] = None,
    ) -> VolumeListResponse:
        response = self._client.transport.get(
            self._client._build_url("/volume"),
            params=dump_request(
                params if params is not None else {},
                VolumeListParams,
            ),
        )
        return VolumeListResponse(**response.data)

    def get(self, volume_id: str) -> Volume:
        response = self._client.transport.get(
            self._client._build_url(f"/volume/{volume_id}")
        )
        return Volume(**response.data)

    def delete(self, volume_id: str) -> VolumeDeleteResult:
        """Delete a volume by id or name. Ambiguous names and active mounts return 409."""
        response = self._client.transport.delete(
            self._client._build_url(f"/volume/{volume_id}")
        )
        return VolumeDeleteResult(**response.data)
