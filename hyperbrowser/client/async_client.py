from typing import Optional

from .managers.async_manager.profile import ProfileManager
from .managers.async_manager.session import SessionManager
from .managers.async_manager.scrape import ScrapeManager
from .managers.async_manager.crawl import CrawlManager
from .managers.async_manager.extension import ExtensionManager
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
        timeout: Optional[int] = 30,
    ):
        super().__init__(AsyncTransport, config, api_key, base_url)
        self.transport.client.timeout = timeout
        self.sessions = SessionManager(self)
        self.scrape = ScrapeManager(self)
        self.crawl = CrawlManager(self)
        self.profiles = ProfileManager(self)
        self.extensions = ExtensionManager(self)

    async def close(self) -> None:
        await self.transport.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
