from typing import List

from ...file_utils import build_open_file_error_message, open_binary_file
from ..extension_create_utils import normalize_extension_create_input
from ..extension_operation_metadata import (
    EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX,
    EXTENSION_OPERATION_METADATA,
)
from ..extension_request_utils import (
    create_extension_resource,
    list_extension_resources,
)
from ..extension_route_constants import (
    EXTENSION_CREATE_ROUTE_PATH,
    EXTENSION_LIST_ROUTE_PATH,
)
from hyperbrowser.models.extension import CreateExtensionParams, ExtensionResponse


class ExtensionManager:
    _OPERATION_METADATA = EXTENSION_OPERATION_METADATA
    _CREATE_ROUTE_PATH = EXTENSION_CREATE_ROUTE_PATH
    _LIST_ROUTE_PATH = EXTENSION_LIST_ROUTE_PATH

    def __init__(self, client):
        self._client = client

    def create(self, params: CreateExtensionParams) -> ExtensionResponse:
        file_path, payload = normalize_extension_create_input(params)

        with open_binary_file(
            file_path,
            open_error_message=build_open_file_error_message(
                file_path,
                prefix=self._OPERATION_METADATA.open_file_error_prefix,
                default_prefix=EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX,
            ),
        ) as extension_file:
            return create_extension_resource(
                client=self._client,
                route_path=self._CREATE_ROUTE_PATH,
                payload=payload,
                file_stream=extension_file,
                model=ExtensionResponse,
                operation_name=self._OPERATION_METADATA.create_operation_name,
            )

    def list(self) -> List[ExtensionResponse]:
        return list_extension_resources(
            client=self._client,
            route_path=self._LIST_ROUTE_PATH,
        )
