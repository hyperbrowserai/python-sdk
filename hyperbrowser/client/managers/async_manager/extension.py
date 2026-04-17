from typing import List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams, ExtensionResponse
from .._uploads import build_extension_upload_request


class ExtensionManager:
    def __init__(self, client):
        self._client = client

    async def create(self, params: CreateExtensionParams) -> ExtensionResponse:
        file_path = params.file_path
        payload = params.model_dump(exclude_none=True, by_alias=True)
        payload.pop("filePath", None)

        response = await self._client.transport.post(
            self._client._build_url("/extensions/add"),
            request_builder=build_extension_upload_request(payload, file_path),
        )
        return ExtensionResponse(**response.data)

    async def list(self) -> List[ExtensionResponse]:
        response = await self._client.transport.get(
            self._client._build_url("/extensions/list"),
        )
        if not isinstance(response.data, dict):
            raise HyperbrowserError(
                f"Expected dict response but got {type(response.data)}",
                original_error=None,
            )
        if "extensions" not in response.data:
            raise HyperbrowserError(
                f"Expected 'extensions' key in response but got {response.data.keys()}",
                original_error=None,
            )
        if not isinstance(response.data["extensions"], list):
            raise HyperbrowserError(
                f"Expected list in 'extensions' key but got {type(response.data['extensions'])}",
                original_error=None,
            )
        return [
            ExtensionResponse(**extension) for extension in response.data["extensions"]
        ]
