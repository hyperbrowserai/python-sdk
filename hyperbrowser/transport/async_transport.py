import asyncio
import httpx
from typing import Any, Dict, Optional

from hyperbrowser.exceptions import HyperbrowserError
from .base import TransportStrategy, APIResponse, is_request_replayable, merge_headers


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

    async def _handle_response(self, response: httpx.Response) -> APIResponse:
        try:
            response.raise_for_status()
            try:
                if not response.content:
                    return APIResponse.from_status(response.status_code)
                return APIResponse(response.json())
            except httpx.DecodingError as e:
                if response.status_code >= 400:
                    raise HyperbrowserError(
                        response.text or "Unknown error occurred",
                        status_code=response.status_code,
                        response=response,
                        original_error=e,
                    )
                return APIResponse.from_status(response.status_code)
        except httpx.HTTPStatusError as e:
            try:
                error_data = response.json()
                message = error_data.get("message") or error_data.get("error") or str(e)
            except Exception:
                message = str(e)
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                response=response,
                original_error=e,
            )
        except httpx.RequestError as e:
            raise HyperbrowserError("Request failed", original_error=e)

    async def post(
        self,
        url: str,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> APIResponse:
        return await self._request(
            "POST",
            url,
            json_data=None if files else data,
            data=data if files else None,
            files=files,
            timeout=timeout,
            replayable=is_request_replayable(files),
        )

    async def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        return await self._request(
            "GET",
            url,
            params=params,
            follow_redirects=follow_redirects,
        )

    async def put(self, url: str, data: Optional[dict] = None) -> APIResponse:
        return await self._request("PUT", url, json_data=data)

    async def delete(self, url: str) -> APIResponse:
        return await self._request("DELETE", url)

    async def send_authenticated(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
    ) -> httpx.Response:
        return await self._exchange(
            method,
            url,
            params=params,
            json_data=json,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
        replayable: bool = True,
    ) -> APIResponse:
        try:
            response = await self._exchange(
                method,
                url,
                params=params,
                json_data=json_data,
                data=data,
                files=files,
                timeout=timeout,
                follow_redirects=follow_redirects,
                replayable=replayable,
            )
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError(
                f"{method.title()} request failed", original_error=e
            )

    async def _exchange(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
        replayable: bool = True,
    ) -> httpx.Response:
        auth_headers, access_token = await self.auth.aauthorize_headers()
        response = await self._send(
            method,
            url,
            params=params,
            json_data=json_data,
            data=data,
            files=files,
            auth_headers=auth_headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )
        if (
            response.status_code == 401
            and getattr(self.auth, "is_oauth", False)
            and replayable
        ):
            await response.aclose()
            retry_headers, _ = await self.auth.aauthorize_headers(
                force_refresh=True,
                rejected_access_token=access_token,
            )
            response = await self._send(
                method,
                url,
                params=params,
                json_data=json_data,
                data=data,
                files=files,
                auth_headers=retry_headers,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
        return response

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict],
        json_data: Optional[Any],
        data: Optional[Any],
        files: Optional[Any],
        auth_headers: Dict[str, str],
        timeout: Optional[float],
        follow_redirects: bool,
    ) -> httpx.Response:
        kwargs: Dict[str, Any] = {
            "headers": merge_headers(auth_headers),
            "follow_redirects": follow_redirects,
        }
        if params is not None:
            kwargs["params"] = params
        if timeout is not None:
            kwargs["timeout"] = timeout
        if json_data is not None:
            kwargs["json"] = json_data
        if data is not None:
            kwargs["data"] = data
        if files is not None:
            kwargs["files"] = files
        return await self.client.request(method, url, **kwargs)
