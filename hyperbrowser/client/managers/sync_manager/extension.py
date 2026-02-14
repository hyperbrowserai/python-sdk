from typing import List

from ...file_utils import open_binary_file
from ..extension_create_utils import normalize_extension_create_input
from ..extension_utils import parse_extension_list_response_data
from ..response_utils import parse_response_model
from hyperbrowser.models.extension import CreateExtensionParams, ExtensionResponse


class ExtensionManager:
    def __init__(self, client):
        self._client = client

    def create(self, params: CreateExtensionParams) -> ExtensionResponse:
        file_path, payload = normalize_extension_create_input(params)

        with open_binary_file(
            file_path,
            open_error_message=f"Failed to open extension file at path: {file_path}",
        ) as extension_file:
            response = self._client.transport.post(
                self._client._build_url("/extensions/add"),
                data=payload,
                files={"file": extension_file},
            )
        return parse_response_model(
            response.data,
            model=ExtensionResponse,
            operation_name="create extension",
        )

    def list(self) -> List[ExtensionResponse]:
        response = self._client.transport.get(
            self._client._build_url("/extensions/list"),
        )
        return parse_extension_list_response_data(response.data)
