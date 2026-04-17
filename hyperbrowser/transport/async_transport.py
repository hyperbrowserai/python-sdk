import asyncio
from typing import Any, Dict, Optional

import httpx

from .base import (
    APIResponse,
    RequestBuilder,
    TransportStrategy,
    build_error_from_response,
    build_network_error,
    normalize_headers,
    prepare_request,
)


class AsyncTransport(TransportStrategy):
    """Asynchronous transport implementation using httpx"""

    def __init__(self, auth):
        self.auth = auth
        self.client = httpx.AsyncClient()
        self._closed = False

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __del__(self):
        if not self._closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.client.aclose())
                else:
                    loop.run_until_complete(self.client.aclose())
            except Exception:
                pass

    async def post(
        self,
        url: str,
        data: Optional[dict] = None,
        files: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        request_builder: Optional[RequestBuilder] = None,
    ) -> APIResponse:
        return await self._request(
            "POST",
            url,
            json_data=data if files is None and request_builder is None else None,
            data=data if files is not None and request_builder is None else None,
            files=files,
            headers=headers,
            request_builder=request_builder,
        )

    async def get(
        self,
        url: str,
        params: Optional[dict] = None,
        follow_redirects: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        return await self._request(
            "GET",
            url,
            params=params,
            follow_redirects=follow_redirects,
            headers=headers,
        )

    async def put(
        self,
        url: str,
        data: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
        request_builder: Optional[RequestBuilder] = None,
    ) -> APIResponse:
        return await self._request(
            "PUT",
            url,
            json_data=data if request_builder is None else None,
            headers=headers,
            request_builder=request_builder,
        )

    async def delete(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        return await self._request("DELETE", url, headers=headers)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        content: Optional[Any] = None,
        files: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        request_builder: Optional[RequestBuilder] = None,
        follow_redirects: bool = False,
    ) -> APIResponse:
        response = None
        request = self._build_request(
            params=params,
            json_data=json_data,
            data=data,
            content=content,
            files=files,
            headers=headers,
            request_builder=request_builder,
        )
        try:
            auth_headers, access_token = await self.auth.aauthorize_headers()
            response = await self._send(
                method,
                url,
                request,
                auth_headers=auth_headers,
                follow_redirects=follow_redirects,
            )

            if response.status_code == 401 and self.auth.is_oauth and request.replayable:
                await response.aclose()
                retry_request = self._build_request(
                    params=params,
                    json_data=json_data,
                    data=data,
                    content=content,
                    files=files,
                    headers=headers,
                    request_builder=request_builder,
                )
                try:
                    retry_headers, _ = await self.auth.aauthorize_headers(
                        force_refresh=True,
                        rejected_access_token=access_token,
                    )
                    retry_response = await self._send(
                        method,
                        url,
                        retry_request,
                        auth_headers=retry_headers,
                        follow_redirects=follow_redirects,
                    )
                finally:
                    retry_request.close()
                return await self._handle_response(retry_response)

            return await self._handle_response(response)
        finally:
            request.close()

    def _build_request(
        self,
        *,
        params: Optional[dict],
        json_data: Optional[Any],
        data: Optional[Any],
        content: Optional[Any],
        files: Optional[Any],
        headers: Optional[Dict[str, str]],
        request_builder: Optional[RequestBuilder],
    ):
        if request_builder is not None:
            return request_builder()
        return prepare_request(
            params=params,
            headers=headers,
            json_data=json_data,
            data=data,
            content=content,
            files=files,
        )

    async def _send(
        self,
        method: str,
        url: str,
        request,
        *,
        auth_headers: Dict[str, str],
        follow_redirects: bool,
    ) -> httpx.Response:
        headers = normalize_headers(request.headers)
        headers.update(normalize_headers(auth_headers))

        try:
            return await self.client.request(
                method,
                url,
                params=request.params,
                headers=headers,
                json=request.json_data,
                data=request.data,
                content=request.content,
                files=request.files,
                follow_redirects=follow_redirects,
            )
        except httpx.RequestError as error:
            raise build_network_error("Request failed", error)

    async def _handle_response(self, response: httpx.Response) -> APIResponse:
        if response.status_code >= 400:
            raise build_error_from_response(response)

        if not response.content:
            return APIResponse.from_status(response.status_code)

        try:
            return APIResponse(response.json(), status_code=response.status_code)
        except ValueError:
            return APIResponse.from_status(response.status_code)
