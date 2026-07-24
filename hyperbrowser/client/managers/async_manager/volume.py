from typing import Union

from hyperbrowser.client._request import dump_request
from hyperbrowser.models.volume import CreateVolumeParams, Volume, VolumeListResponse
from hyperbrowser.types import CreateVolumeParams as CreateVolumeParamsDict


class VolumeManager:
    def __init__(self, client):
        self._client = client

    async def create(
        self,
        params: Union[CreateVolumeParamsDict, CreateVolumeParams],
    ) -> Volume:
        response = await self._client.transport.post(
            self._client._build_url("/volume"),
            data=dump_request(params, CreateVolumeParams),
        )
        return Volume(**response.data)

    async def list(self) -> VolumeListResponse:
        response = await self._client.transport.get(self._client._build_url("/volume"))
        return VolumeListResponse(**response.data)

    async def get(self, volume_id: str) -> Volume:
        response = await self._client.transport.get(
            self._client._build_url(f"/volume/{volume_id}")
        )
        return Volume(**response.data)
