from typing import Any, Type, TypeVar

from .job_request_utils import (
    get_job,
    get_job_async,
    get_job_status,
    get_job_status_async,
)

T = TypeVar("T")


def get_agent_task(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return get_job(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        params=None,
        model=model,
        operation_name=operation_name,
    )


def get_agent_task_status(
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


async def get_agent_task_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    return await get_job_async(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        params=None,
        model=model,
        operation_name=operation_name,
    )


async def get_agent_task_status_async(
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
