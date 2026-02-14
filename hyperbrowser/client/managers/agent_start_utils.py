from typing import Any, Dict, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def start_agent_task(
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


async def start_agent_task_async(
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
