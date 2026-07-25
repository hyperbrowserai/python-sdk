import os
from typing import List, Union

from hyperbrowser.client._request import coerce_request, dump_request
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams, ExtensionResponse
from hyperbrowser.types import CreateExtensionParams as CreateExtensionParamsDict


class ExtensionManager:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        params: Union[CreateExtensionParamsDict, CreateExtensionParams],
    ) -> ExtensionResponse:
        normalized = coerce_request(params, CreateExtensionParams)
        file_path = normalized.file_path

        # Check if file exists before trying to open it
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Extension file not found at path: {file_path}")

        normalized = normalized.model_copy(update={"file_path": None})
        with open(file_path, "rb") as file_obj:
            response = self._client.transport.post(
                self._client._build_url("/extensions/add"),
                data=dump_request(normalized, CreateExtensionParams),
                files={"file": file_obj},
            )
        return ExtensionResponse(**response.data)

    def list(self) -> List[ExtensionResponse]:
        response = self._client.transport.get(
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
