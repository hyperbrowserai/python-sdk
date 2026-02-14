from typing import Any, Dict, Optional, Type, TypeVar

from .session_utils import (
    parse_session_recordings_response_data,
    parse_session_response_model,
)

T = TypeVar("T")


def post_session_resource(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
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


def get_session_resource(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = False,
) -> Any:
    if follow_redirects:
        response = client.transport.get(
            client._build_url(route_path),
            params,
            True,
        )
    else:
        response = client.transport.get(
            client._build_url(route_path),
            params=params,
        )
    return response.data


def put_session_resource(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    response = client.transport.put(
        client._build_url(route_path),
        data=data,
    )
    return response.data


async def post_session_resource_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
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


async def get_session_resource_async(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = False,
) -> Any:
    if follow_redirects:
        response = await client.transport.get(
            client._build_url(route_path),
            params,
            True,
        )
    else:
        response = await client.transport.get(
            client._build_url(route_path),
            params=params,
        )
    return response.data


async def put_session_resource_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    response = await client.transport.put(
        client._build_url(route_path),
        data=data,
    )
    return response.data


def post_session_model(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = post_session_resource(
        client=client,
        route_path=route_path,
        data=data,
        files=files,
    )
    return parse_session_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


def get_session_model(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = get_session_resource(
        client=client,
        route_path=route_path,
        params=params,
    )
    return parse_session_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


def put_session_model(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = put_session_resource(
        client=client,
        route_path=route_path,
        data=data,
    )
    return parse_session_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


def get_session_recordings(
    *,
    client: Any,
    route_path: str,
) -> Any:
    response_data = get_session_resource(
        client=client,
        route_path=route_path,
        follow_redirects=True,
    )
    return parse_session_recordings_response_data(response_data)


async def post_session_model_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = await post_session_resource_async(
        client=client,
        route_path=route_path,
        data=data,
        files=files,
    )
    return parse_session_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


async def get_session_model_async(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = await get_session_resource_async(
        client=client,
        route_path=route_path,
        params=params,
    )
    return parse_session_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


async def put_session_model_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
    model: Type[T],
    operation_name: str,
) -> T:
    response_data = await put_session_resource_async(
        client=client,
        route_path=route_path,
        data=data,
    )
    return parse_session_response_model(
        response_data,
        model=model,
        operation_name=operation_name,
    )


async def get_session_recordings_async(
    *,
    client: Any,
    route_path: str,
) -> Any:
    response_data = await get_session_resource_async(
        client=client,
        route_path=route_path,
        follow_redirects=True,
    )
    return parse_session_recordings_response_data(response_data)
