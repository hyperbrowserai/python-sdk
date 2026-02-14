from typing import Any, IO, List, Type, TypeVar

from .extension_utils import parse_extension_list_response_data
from .model_request_utils import post_model_request, post_model_request_async
from hyperbrowser.models.extension import ExtensionResponse

T = TypeVar("T")


def create_extension_resource(
    *,
    client: Any,
    route_path: str,
    payload: Any,
    file_stream: IO,
    model: Type[T],
    operation_name: str,
) -> T:
    return post_model_request(
        client=client,
        route_path=route_path,
        data=payload,
        files={"file": file_stream},
        model=model,
        operation_name=operation_name,
    )


def list_extension_resources(
    *,
    client: Any,
    route_path: str,
) -> List[ExtensionResponse]:
    response = client.transport.get(
        client._build_url(route_path),
    )
    return parse_extension_list_response_data(response.data)


async def create_extension_resource_async(
    *,
    client: Any,
    route_path: str,
    payload: Any,
    file_stream: IO,
    model: Type[T],
    operation_name: str,
) -> T:
    return await post_model_request_async(
        client=client,
        route_path=route_path,
        data=payload,
        files={"file": file_stream},
        model=model,
        operation_name=operation_name,
    )


async def list_extension_resources_async(
    *,
    client: Any,
    route_path: str,
) -> List[ExtensionResponse]:
    response = await client.transport.get(
        client._build_url(route_path),
    )
    return parse_extension_list_response_data(response.data)
