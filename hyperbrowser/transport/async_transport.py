import aiohttp
from typing import Optional
from .base import TransportStrategy, APIResponse

class AsyncTransport(TransportStrategy):
    """Asynchronous transport implementation using aiohttp"""
    def __init__(self, api_key: str):
        self.session = aiohttp.ClientSession(headers={"x-api-key": api_key})

    async def close(self) -> None:
        await self.session.close()

    async def post(self, url: str) -> APIResponse:
        async with self.session.post(url) as response:
            response.raise_for_status()
            try:
                if response.content_length is None or response.content_length == 0:
                    return APIResponse.from_status(response.status)
                return APIResponse(await response.json())
            except aiohttp.ContentTypeError:
                return APIResponse.from_status(response.status)

    async def get(self, url: str, params: Optional[dict] = None) -> APIResponse:
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            try:
                if response.content_length is None or response.content_length == 0:
                    return APIResponse.from_status(response.status)
                return APIResponse(await response.json())
            except aiohttp.ContentTypeError:
                return APIResponse.from_status(response.status)

    async def put(self, url: str) -> APIResponse:
        async with self.session.put(url) as response:
            response.raise_for_status()
            try:
                if response.content_length is None or response.content_length == 0:
                    return APIResponse.from_status(response.status)
                return APIResponse(await response.json())
            except aiohttp.ContentTypeError:
                return APIResponse.from_status(response.status)