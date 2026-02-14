from typing import Any, Dict, Optional


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
