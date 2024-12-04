from typing import Optional
from ..transport.async_transport import AsyncTransport
from .base import HyperbrowserBase
from ..models.session import BasicResponse, SessionDetail, SessionListParams, SessionListResponse
from ..config import ClientConfig

class AsyncHyperbrowser(HyperbrowserBase):
    """Asynchronous Hyperbrowser client"""
    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(AsyncTransport, config, api_key, base_url)

    async def create_session(self) -> SessionDetail:
        response = await self.transport.post(self._build_url("/session"))
        return SessionDetail(**response.data)

    async def get_session(self, id: str) -> SessionDetail:
        response = await self.transport.get(self._build_url(f"/session/{id}"))
        return SessionDetail(**response.data)

    async def stop_session(self, id: str) -> BasicResponse:
        response = await self.transport.put(self._build_url(f"/session/{id}/stop"))
        return BasicResponse(**response.data)

    async def get_session_list(self, params: SessionListParams = SessionListParams()) -> SessionListResponse:
        response = await self.transport.get(
            self._build_url("/sessions"),
            params=params.__dict__
        )
        return SessionListResponse(**response.data)

    async def close(self) -> None:
        await self.transport.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
