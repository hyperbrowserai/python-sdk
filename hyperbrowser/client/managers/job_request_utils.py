from typing import Any, Dict, Optional, Type, TypeVar

from .job_route_builders import (
    build_job_action_route,
    build_job_route,
    build_job_status_route,
)
from .model_request_utils import (
    get_model_request,
    get_model_request_async,
    post_model_request,
    post_model_request_async,
    put_model_request,
    put_model_request_async,
)

T = TypeVar("T")


def start_job(
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


def get_job_status(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return get_model_request(
        client=client,
        route_path=build_job_status_route(route_prefix, job_id),
        params=None,
        model=model,
        operation_name=operation_name,
    )


def get_job(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    return get_model_request(
        client=client,
        route_path=build_job_route(route_prefix, job_id),
        params=params,
        model=model,
        operation_name=operation_name,
    )


async def start_job_async(
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


async def get_job_status_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return await get_model_request_async(
        client=client,
        route_path=build_job_status_route(route_prefix, job_id),
        params=None,
        model=model,
        operation_name=operation_name,
    )


async def get_job_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    return await get_model_request_async(
        client=client,
        route_path=build_job_route(route_prefix, job_id),
        params=params,
        model=model,
        operation_name=operation_name,
    )


def put_job_action(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    action_suffix: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return put_model_request(
        client=client,
        route_path=build_job_action_route(route_prefix, job_id, action_suffix),
        data=None,
        model=model,
        operation_name=operation_name,
    )


async def put_job_action_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    action_suffix: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return await put_model_request_async(
        client=client,
        route_path=build_job_action_route(route_prefix, job_id, action_suffix),
        data=None,
        model=model,
        operation_name=operation_name,
    )
