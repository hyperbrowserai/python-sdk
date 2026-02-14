from typing import Any

from hyperbrowser.models import ComputerActionResponse

from .response_utils import parse_response_model


def execute_computer_action_request(
    *,
    client: Any,
    endpoint: str,
    payload: dict[str, Any],
    operation_name: str,
) -> ComputerActionResponse:
    response = client.transport.post(
        endpoint,
        data=payload,
    )
    return parse_response_model(
        response.data,
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
    response = await client.transport.post(
        endpoint,
        data=payload,
    )
    return parse_response_model(
        response.data,
        model=ComputerActionResponse,
        operation_name=operation_name,
    )
