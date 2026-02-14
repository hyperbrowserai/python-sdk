from typing import Any, Dict, Optional, Type, TypeVar

from .model_request_utils import (
    get_model_response_data,
    get_model_response_data_async,
    post_model_response_data,
    post_model_response_data_async,
    put_model_response_data,
    put_model_response_data_async,
)
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
    return post_model_response_data(
        client=client,
        route_path=route_path,
        data=data,
        files=files,
    )


def get_session_resource(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = False,
) -> Any:
    return get_model_response_data(
        client=client,
        route_path=route_path,
        params=params,
        follow_redirects=follow_redirects,
    )


def put_session_resource(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    return put_model_response_data(
        client=client,
        route_path=route_path,
        data=data,
    )


async def post_session_resource_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
) -> Any:
    return await post_model_response_data_async(
        client=client,
        route_path=route_path,
        data=data,
        files=files,
    )


async def get_session_resource_async(
    *,
    client: Any,
    route_path: str,
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = False,
) -> Any:
    return await get_model_response_data_async(
        client=client,
        route_path=route_path,
        params=params,
        follow_redirects=follow_redirects,
    )


async def put_session_resource_async(
    *,
    client: Any,
    route_path: str,
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    return await put_model_response_data_async(
        client=client,
        route_path=route_path,
        data=data,
    )


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
