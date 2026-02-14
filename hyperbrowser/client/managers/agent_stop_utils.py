from typing import Any

from hyperbrowser.models import BasicResponse

from .response_utils import parse_response_model


def stop_agent_task(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    operation_name: str,
) -> BasicResponse:
    response = client.transport.put(
        client._build_url(f"{route_prefix}/{job_id}/stop"),
    )
    return parse_response_model(
        response.data,
        model=BasicResponse,
        operation_name=operation_name,
    )


async def stop_agent_task_async(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    operation_name: str,
) -> BasicResponse:
    response = await client.transport.put(
        client._build_url(f"{route_prefix}/{job_id}/stop"),
    )
    return parse_response_model(
        response.data,
        model=BasicResponse,
        operation_name=operation_name,
    )
