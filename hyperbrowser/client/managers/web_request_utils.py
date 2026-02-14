from typing import Any, Dict, Optional, Type, TypeVar

from .job_request_utils import (
    get_job,
    get_job_async,
    get_job_status,
    get_job_status_async,
    start_job,
    start_job_async,
)

T = TypeVar("T")


def start_web_job(
    *,
    client: Any,
    route_prefix: str,
    payload: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    return start_job(
        client=client,
        route_prefix=route_prefix,
        payload=payload,
        model=model,
        operation_name=operation_name,
    )


def get_web_job_status(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return get_job_status(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        model=model,
        operation_name=operation_name,
    )


def get_web_job(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    return get_job(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        params=params,
        model=model,
        operation_name=operation_name,
    )


async def start_web_job_async(
    *,
    client: Any,
    route_prefix: str,
    payload: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    return await start_job_async(
        client=client,
        route_prefix=route_prefix,
        payload=payload,
        model=model,
        operation_name=operation_name,
    )


async def get_web_job_status_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return await get_job_status_async(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        model=model,
        operation_name=operation_name,
    )


async def get_web_job_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    return await get_job_async(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        params=params,
        model=model,
        operation_name=operation_name,
    )
