from typing import Any, Type, TypeVar

from .model_request_utils import get_model_request, get_model_request_async

T = TypeVar("T")


def get_team_resource(
    *,
    client: Any,
    route_path: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return get_model_request(
        client=client,
        route_path=route_path,
        params=None,
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
    return await get_model_request_async(
        client=client,
        route_path=route_path,
        params=None,
        model=model,
        operation_name=operation_name,
    )
