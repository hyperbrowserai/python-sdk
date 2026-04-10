from hyperbrowser.models.volume import CreateVolumeParams, Volume, VolumeListResponse


class VolumeManager:
    def __init__(self, client):
        self._client = client

    async def create(self, params: CreateVolumeParams) -> Volume:
        if not isinstance(params, CreateVolumeParams):
            raise TypeError("params must be a CreateVolumeParams instance")

        response = await self._client.transport.post(
            self._client._build_url("/volume"),
            data=params.model_dump(exclude_none=True, by_alias=True),
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
