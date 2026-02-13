import httpx
from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.version import __version__
from .base import APIResponse, AsyncTransportStrategy


class AsyncTransport(AsyncTransportStrategy):
    """Asynchronous transport implementation using httpx"""

    def __init__(self, api_key: str, headers: Optional[dict] = None):
        merged_headers = {
            "x-api-key": api_key,
            "User-Agent": f"hyperbrowser-python-sdk/{__version__}",
        }
        if headers:
            merged_headers.update(headers)
        self.client = httpx.AsyncClient(headers=merged_headers)
        self._closed = False

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

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
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse:
        try:
            if files:
                response = await self.client.post(url, data=data, files=files)
            else:
                response = await self.client.post(url, json=data)
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Post request failed", original_error=e)

    async def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        try:
            response = await self.client.get(
                url, params=params, follow_redirects=follow_redirects
            )
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Get request failed", original_error=e)

    async def put(self, url: str, data: Optional[dict] = None) -> APIResponse:
        try:
            response = await self.client.put(url, json=data)
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Put request failed", original_error=e)

    async def delete(self, url: str) -> APIResponse:
        try:
            response = await self.client.delete(url)
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Delete request failed", original_error=e)
