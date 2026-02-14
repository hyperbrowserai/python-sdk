from typing import Any

from hyperbrowser.models import BasicResponse

from .job_request_utils import put_job_action, put_job_action_async


def stop_agent_task(
    *,
    client: Any,
    route_prefix: str,
    job_id: str,
    operation_name: str,
) -> BasicResponse:
    return put_job_action(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        action_suffix="/stop",
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
    return await put_job_action_async(
        client=client,
        route_prefix=route_prefix,
        job_id=job_id,
        action_suffix="/stop",
        model=BasicResponse,
        operation_name=operation_name,
    )
