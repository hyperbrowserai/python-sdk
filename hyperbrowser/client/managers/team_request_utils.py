from typing import Any, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def get_team_resource(
    *,
    client: Any,
    route_path: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.get(
        client._build_url(route_path),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def get_team_resource_async(
    *,
    client: Any,
    route_path: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.get(
        client._build_url(route_path),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )
