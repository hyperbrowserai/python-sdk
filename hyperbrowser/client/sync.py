from typing import Optional
from ..transport.sync import SyncTransport
from .base import HyperbrowserBase
from ..models.session import (
    BasicResponse,
    SessionDetail,
    SessionListParams,
    SessionListResponse,
)
from ..config import ClientConfig


class Hyperbrowser(HyperbrowserBase):
    """Synchronous Hyperbrowser client"""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(SyncTransport, config, api_key, base_url)

    def create_session(self) -> SessionDetail:
        response = self.transport.post(self._build_url("/session"))
        return SessionDetail(**response.data)

    def get_session(self, id: str) -> SessionDetail:
        response = self.transport.get(self._build_url(f"/session/{id}"))
        return SessionDetail(**response.data)

    def stop_session(self, id: str) -> BasicResponse:
        response = self.transport.put(self._build_url(f"/session/{id}/stop"))
        return BasicResponse(**response.data)

    def get_session_list(self, params: SessionListParams) -> SessionListResponse:
        response = self.transport.get(
            self._build_url("/sessions"), params=params.__dict__
        )
        return SessionListResponse(**response.data)

    def close(self) -> None:
        self.transport.close()
