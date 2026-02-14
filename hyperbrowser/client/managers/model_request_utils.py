from typing import Any, Dict, Optional, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def post_model_request(
    *,
    client: Any,
    route_path: str,
    data: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.post(
        client._build_url(route_path),
        data=data,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


def get_model_request(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.get(
        client._build_url(route_path),
        params=params,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


def delete_model_request(
    *,
    client: Any,
    route_path: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.delete(
        client._build_url(route_path),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


def put_model_request(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.put(
        client._build_url(route_path),
        data=data,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def post_model_request_async(
    *,
    client: Any,
    route_path: str,
    data: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.post(
        client._build_url(route_path),
        data=data,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def get_model_request_async(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.get(
        client._build_url(route_path),
        params=params,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def delete_model_request_async(
    *,
    client: Any,
    route_path: str,
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.delete(
        client._build_url(route_path),
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def put_model_request_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.put(
        client._build_url(route_path),
        data=data,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )
