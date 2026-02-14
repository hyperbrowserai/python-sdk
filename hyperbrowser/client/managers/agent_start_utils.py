from typing import Any, Dict, Type, TypeVar

from .job_request_utils import start_job, start_job_async

T = TypeVar("T")


def start_agent_task(
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


async def start_agent_task_async(
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
