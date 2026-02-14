from typing import Any

from hyperbrowser.models import ComputerActionResponse

from .model_request_utils import (
    post_model_request_to_endpoint,
    post_model_request_to_endpoint_async,
)


def execute_computer_action_request(
    *,
    client: Any,
    endpoint: str,
    payload: dict[str, Any],
    operation_name: str,
) -> ComputerActionResponse:
    return post_model_request_to_endpoint(
        client=client,
        endpoint=endpoint,
        data=payload,
        model=ComputerActionResponse,
        operation_name=operation_name,
    )


async def execute_computer_action_request_async(
    *,
    client: Any,
    endpoint: str,
    payload: dict[str, Any],
    operation_name: str,
) -> ComputerActionResponse:
    return await post_model_request_to_endpoint_async(
        client=client,
        endpoint=endpoint,
        data=payload,
        model=ComputerActionResponse,
        operation_name=operation_name,
    )
