from typing import Any, Dict, Optional, Type, TypeVar

from .model_request_utils import (
    delete_model_request,
    delete_model_request_async,
    get_model_request,
    get_model_request_async,
    post_model_request,
    post_model_request_async,
)
from .profile_route_constants import build_profile_route

T = TypeVar("T")


def create_profile_resource(
    *,
    client: Any,
    route_prefix: str,
    payload: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    return post_model_request(
        client=client,
        route_path=route_prefix,
        data=payload,
        model=model,
        operation_name=operation_name,
    )


def get_profile_resource(
    *,
    client: Any,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return get_model_request(
        client=client,
        route_path=build_profile_route(profile_id),
        params=None,
        model=model,
        operation_name=operation_name,
    )


def delete_profile_resource(
    *,
    client: Any,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return delete_model_request(
        client=client,
        route_path=build_profile_route(profile_id),
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
    return get_model_request(
        client=client,
        route_path=list_route_path,
        params=params,
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
    return await post_model_request_async(
        client=client,
        route_path=route_prefix,
        data=payload,
        model=model,
        operation_name=operation_name,
    )


async def get_profile_resource_async(
    *,
    client: Any,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return await get_model_request_async(
        client=client,
        route_path=build_profile_route(profile_id),
        params=None,
        model=model,
        operation_name=operation_name,
    )


async def delete_profile_resource_async(
    *,
    client: Any,
    profile_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return await delete_model_request_async(
        client=client,
        route_path=build_profile_route(profile_id),
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
    return await get_model_request_async(
        client=client,
        route_path=list_route_path,
        params=params,
        model=model,
        operation_name=operation_name,
    )
