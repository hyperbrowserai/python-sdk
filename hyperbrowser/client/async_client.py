from typing import Optional
from .managers.async_manager.session import SessionManager
from .managers.async_manager.scrape import ScrapeManager
from .managers.async_manager.crawl import CrawlManager
from .base import HyperbrowserBase
from ..transport.async_transport import AsyncTransport
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
        self.sessions = SessionManager(self)
        self.scrape = ScrapeManager(self)
        self.crawl = CrawlManager(self)

    async def close(self) -> None:
        await self.transport.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
