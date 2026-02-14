from typing import Any, Dict, Optional, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def start_job(
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


def get_job_status(
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


def get_job(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}"),
        params=params,
    )
    return parse_response_model(
        response.data,
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
    response = await client.transport.post(
        client._build_url(route_prefix),
        data=payload,
    )
    return parse_response_model(
        response.data,
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
    response = await client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}/status"),
    )
    return parse_response_model(
        response.data,
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
    response = await client.transport.get(
        client._build_url(f"{route_prefix}/{job_id}"),
        params=params,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )
