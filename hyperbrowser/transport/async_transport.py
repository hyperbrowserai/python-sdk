import asyncio
import httpx
from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from .base import TransportStrategy, APIResponse


class AsyncTransport(TransportStrategy):
    """Asynchronous transport implementation using httpx"""

    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(headers={"x-api-key": api_key})
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
            except:
                message = str(e)
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                response=response,
                original_error=e,
            )
        except httpx.RequestError as e:
            raise HyperbrowserError("Request failed", original_error=e)

    async def post(self, url: str, data: Optional[dict] = None) -> APIResponse:
        try:
            response = await self.client.post(url, json=data)
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Post request failed", original_error=e)

    async def get(self, url: str, params: Optional[dict] = None) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        try:
            response = await self.client.get(url, params=params)
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Get request failed", original_error=e)

    async def put(self, url: str) -> APIResponse:
        try:
            response = await self.client.put(url)
            return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Put request failed", original_error=e)
