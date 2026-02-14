from typing import Any, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def get_agent_task(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}"),
    )
    return parse_response_model(
        response.data,
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
    response = client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}/status"),
    )
    return parse_response_model(
        response.data,
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
    response = await client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}"),
    )
    return parse_response_model(
        response.data,
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
    response = await client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}/status"),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )
