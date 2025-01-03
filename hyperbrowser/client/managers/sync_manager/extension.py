import os
from typing import List

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams, ExtensionResponse


class ExtensionManager:
    def __init__(self, client):
        self._client = client

    def create(self, params: CreateExtensionParams) -> ExtensionResponse:
        file_path = params.file_path
        params.file_path = None

        # Check if file exists before trying to open it
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Extension file not found at path: {file_path}")

        response = self._client.transport.post(
            self._client._build_url("/extensions/add"),
            data=(
                {}
                if params is None
                else params.model_dump(exclude_none=True, by_alias=True)
            ),
            files={"file": open(file_path, "rb")},
        )
        return ExtensionResponse(**response.data)

    def list(self) -> List[ExtensionResponse]:
        response = self._client.transport.get(
            self._client._build_url("/extensions/list"),
        )
        if not isinstance(response.data, list):
            raise HyperbrowserError(
                f"Expected list response but got {type(response.data)}",
                original_error=None,
            )
        return [ExtensionResponse(**extension) for extension in response.data]
