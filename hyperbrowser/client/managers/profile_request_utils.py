from typing import Any, Dict, Optional, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def create_profile_resource(
    *,
    client: Any,
    route_prefix: str,
    payload: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.post(
        client._build_url(route_prefix),
        data=payload,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


def get_profile_resource(
    *,
    client: Any,
    route_prefix: str,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.get(
        client._build_url(f"{route_prefix}/{profile_id}"),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


def delete_profile_resource(
    *,
    client: Any,
    route_prefix: str,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.delete(
        client._build_url(f"{route_prefix}/{profile_id}"),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


def list_profile_resources(
    *,
    client: Any,
    list_route_path: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.get(
        client._build_url(list_route_path),
        params=params,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def create_profile_resource_async(
    *,
    client: Any,
    route_prefix: str,
    payload: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.post(
        client._build_url(route_prefix),
        data=payload,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def get_profile_resource_async(
    *,
    client: Any,
    route_prefix: str,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.get(
        client._build_url(f"{route_prefix}/{profile_id}"),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def delete_profile_resource_async(
    *,
    client: Any,
    route_prefix: str,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.delete(
        client._build_url(f"{route_prefix}/{profile_id}"),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def list_profile_resources_async(
    *,
    client: Any,
    list_route_path: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.get(
        client._build_url(list_route_path),
        params=params,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )
