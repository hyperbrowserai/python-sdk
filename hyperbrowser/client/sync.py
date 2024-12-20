from typing import Optional
from .managers.sync_manager.session import SessionManager
from .managers.sync_manager.scrape import ScrapeManager
from .managers.sync_manager.crawl import CrawlManager
from .base import HyperbrowserBase
from ..transport.sync import SyncTransport
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
        self.sessions = SessionManager(self)
        self.scrape = ScrapeManager(self)
        self.crawl = CrawlManager(self)

    def close(self) -> None:
        self.transport.close()
