from types import TracebackType
from typing import Mapping, Optional, Type

from ..config import ClientConfig
from ..transport.async_transport import AsyncTransport
from .base import HyperbrowserBase
from .timeout_utils import validate_timeout_seconds
from .managers.async_manager.web import WebManager
from .managers.async_manager.agents import Agents
from .managers.async_manager.crawl import CrawlManager
from .managers.async_manager.extension import ExtensionManager
from .managers.async_manager.extract import ExtractManager
from .managers.async_manager.profile import ProfileManager
from .managers.async_manager.scrape import ScrapeManager
from .managers.async_manager.session import SessionManager
from .managers.async_manager.team import TeamManager
from .managers.async_manager.computer_action import ComputerActionManager


class AsyncHyperbrowser(HyperbrowserBase):
    """Asynchronous Hyperbrowser client"""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = 30,
    ):
        timeout = validate_timeout_seconds(timeout)
        super().__init__(AsyncTransport, config, api_key, base_url, headers)
        self.transport.client.timeout = timeout
        self.sessions = SessionManager(self)
        self.web = WebManager(self)
        self.scrape = ScrapeManager(self)
        self.crawl = CrawlManager(self)
        self.extract = ExtractManager(self)
        self.profiles = ProfileManager(self)
        self.extensions = ExtensionManager(self)
        self.agents = Agents(self)
        self.team = TeamManager(self)
        self.computer_action = ComputerActionManager(self)

    async def close(self) -> None:
        await self.transport.close()

    async def __aenter__(self) -> "AsyncHyperbrowser":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()
