import asyncio
import aiohttp
from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from .base import TransportStrategy, APIResponse


class AsyncTransport(TransportStrategy):
    """Asynchronous transport implementation using aiohttp"""

    def __init__(self, api_key: str):
        self.session = aiohttp.ClientSession(headers={"x-api-key": api_key})
        self._closed = False

    async def close(self) -> None:
        if not self._closed and not self.session.closed:
            self._closed = True
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __del__(self):
        if not self._closed and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except Exception:
                pass

    async def _handle_response(self, response: aiohttp.ClientResponse) -> APIResponse:
        try:
            response.raise_for_status()
            try:
                if response.content_length is None or response.content_length == 0:
                    return APIResponse.from_status(response.status)
                return APIResponse(await response.json())
            except aiohttp.ContentTypeError as e:
                if response.status >= 400:
                    text = await response.text()
                    raise HyperbrowserError(
                        text or "Unknown error occurred",
                        status_code=response.status,
                        response=response,
                        original_error=e,
                    )
                return APIResponse.from_status(response.status)
        except aiohttp.ClientResponseError as e:
            try:
                error_data = await response.json()
                message = error_data.get("message") or error_data.get("error") or str(e)
            except:
                message = str(e)
            raise HyperbrowserError(
                message,
                status_code=response.status,
                response=response,
                original_error=e,
            )
        except aiohttp.ClientError as e:
            raise HyperbrowserError("Request failed", original_error=e)

    async def post(self, url: str) -> APIResponse:
        try:
            async with self.session.post(url) as response:
                return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Post request failed", original_error=e)

    async def get(self, url: str, params: Optional[dict] = None) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        try:
            async with self.session.get(url, params=params) as response:
                return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Get request failed", original_error=e)

    async def put(self, url: str) -> APIResponse:
        try:
            async with self.session.put(url) as response:
                return await self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Put request failed", original_error=e)
