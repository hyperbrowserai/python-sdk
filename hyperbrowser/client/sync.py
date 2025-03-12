from typing import Optional

from ..config import ClientConfig
from ..transport.sync import SyncTransport
from .base import HyperbrowserBase
from .managers.sync_manager.agents import Agents
from .managers.sync_manager.crawl import CrawlManager
from .managers.sync_manager.extension import ExtensionManager
from .managers.sync_manager.extract import ExtractManager
from .managers.sync_manager.profile import ProfileManager
from .managers.sync_manager.scrape import ScrapeManager
from .managers.sync_manager.session import SessionManager


class Hyperbrowser(HyperbrowserBase):
    """Synchronous Hyperbrowser client"""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = 30,
    ):
        super().__init__(SyncTransport, config, api_key, base_url)
        self.transport.client.timeout = timeout
        self.sessions = SessionManager(self)
        self.scrape = ScrapeManager(self)
        self.crawl = CrawlManager(self)
        self.extract = ExtractManager(self)
        self.profiles = ProfileManager(self)
        self.extensions = ExtensionManager(self)
        self.agents = Agents(self)

    def close(self) -> None:
        self.transport.close()
