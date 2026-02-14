from typing import Any, Dict, Optional, Type, TypeVar

from .response_utils import parse_response_model

T = TypeVar("T")


def post_model_request(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
    files: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = post_model_response_data(
        client=client,
        route_path=route_path,
        data=data,
        files=files,
    )
    return parse_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


def post_model_response_data(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
    files: Optional[Dict[str, Any]] = None,
) -> Any:
    if files is None:
        response = client.transport.post(
            client._build_url(route_path),
            data=data,
        )
    else:
        response = client.transport.post(
            client._build_url(route_path),
            data=data,
            files=files,
        )
    return response.data


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


def get_model_response_data(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = False,
) -> Any:
    if follow_redirects:
        response = client.transport.get(
            client._build_url(route_path),
            params=params,
            follow_redirects=True,
        )
    else:
        response = client.transport.get(
            client._build_url(route_path),
            params=params,
        )
    return response.data


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
    response_data = put_model_response_data(
        client=client,
        route_path=route_path,
        data=data,
    )
    return parse_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


def put_model_response_data(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
) -> Any:
    response = client.transport.put(
        client._build_url(route_path),
        data=data,
    )
    return response.data


async def post_model_request_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
    files: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = await post_model_response_data_async(
        client=client,
        route_path=route_path,
        data=data,
        files=files,
    )
    return parse_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


async def post_model_response_data_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
    files: Optional[Dict[str, Any]] = None,
) -> Any:
    if files is None:
        response = await client.transport.post(
            client._build_url(route_path),
            data=data,
        )
    else:
        response = await client.transport.post(
            client._build_url(route_path),
            data=data,
            files=files,
        )
    return response.data


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


async def get_model_response_data_async(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = False,
) -> Any:
    if follow_redirects:
        response = await client.transport.get(
            client._build_url(route_path),
            params=params,
            follow_redirects=True,
        )
    else:
        response = await client.transport.get(
            client._build_url(route_path),
            params=params,
        )
    return response.data


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
    response_data = await put_model_response_data_async(
        client=client,
        route_path=route_path,
        data=data,
    )
    return parse_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


async def put_model_response_data_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]],
) -> Any:
    response = await client.transport.put(
        client._build_url(route_path),
        data=data,
    )
    return response.data


def post_model_request_to_endpoint(
    *,
    client: Any,
    endpoint: str,
    data: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    response = client.transport.post(
        endpoint,
        data=data,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )


async def post_model_request_to_endpoint_async(
    *,
    client: Any,
    endpoint: str,
    data: Dict[str, Any],
    model: Type[T],
    operation_name: str,
) -> T:
    response = await client.transport.post(
        endpoint,
        data=data,
    )
    return parse_response_model(
        response.data,
        model=model,
        operation_name=operation_name,
    )
