from typing import List

from hyperbrowser.exceptions import HyperbrowserError
from ...file_utils import ensure_existing_file_path
from ..serialization_utils import serialize_model_dump_to_dict
from ..extension_utils import parse_extension_list_response_data
from ..response_utils import parse_response_model
from hyperbrowser.models.extension import CreateExtensionParams, ExtensionResponse


class ExtensionManager:
    def __init__(self, client):
        self._client = client

    async def create(self, params: CreateExtensionParams) -> ExtensionResponse:
        if type(params) is not CreateExtensionParams:
            raise HyperbrowserError("params must be CreateExtensionParams")
        try:
            raw_file_path = params.file_path
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "params.file_path is invalid",
                original_error=exc,
            ) from exc
        payload = serialize_model_dump_to_dict(
            params,
            error_message="Failed to serialize extension create params",
        )
        payload.pop("filePath", None)

        file_path = ensure_existing_file_path(
            raw_file_path,
            missing_file_message=f"Extension file not found at path: {raw_file_path}",
            not_file_message=f"Extension file path must point to a file: {raw_file_path}",
        )

        try:
            with open(file_path, "rb") as extension_file:
                response = await self._client.transport.post(
                    self._client._build_url("/extensions/add"),
                    data=payload,
                    files={"file": extension_file},
                )
        except OSError as exc:
            raise HyperbrowserError(
                f"Failed to open extension file at path: {file_path}",
                original_error=exc,
            ) from exc
        return parse_response_model(
            response.data,
            model=ExtensionResponse,
            operation_name="create extension",
        )

    async def list(self) -> List[ExtensionResponse]:
        response = await self._client.transport.get(
            self._client._build_url("/extensions/list"),
        )
        return parse_extension_list_response_data(response.data)
