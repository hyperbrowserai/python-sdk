import inspect

from hyperbrowser.client.managers.async_manager.agents.browser_use import (
    BrowserUseManager as AsyncBrowserUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.claude_computer_use import (
    ClaudeComputerUseManager as AsyncClaudeComputerUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.cua import (
    CuaManager as AsyncCuaManager,
)
from hyperbrowser.client.managers.async_manager.agents.gemini_computer_use import (
    GeminiComputerUseManager as AsyncGeminiComputerUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.hyper_agent import (
    HyperAgentManager as AsyncHyperAgentManager,
)
from hyperbrowser.client.managers.async_manager.crawl import (
    CrawlManager as AsyncCrawlManager,
)
from hyperbrowser.client.managers.async_manager.extract import (
    ExtractManager as AsyncExtractManager,
)
from hyperbrowser.client.managers.async_manager.scrape import (
    BatchScrapeManager as AsyncBatchScrapeManager,
    ScrapeManager as AsyncScrapeManager,
)
from hyperbrowser.client.managers.async_manager.web.batch_fetch import (
    BatchFetchManager as AsyncBatchFetchManager,
)
from hyperbrowser.client.managers.async_manager.web.crawl import (
    WebCrawlManager as AsyncWebCrawlManager,
)
from hyperbrowser.client.managers.sync_manager.agents.browser_use import (
    BrowserUseManager as SyncBrowserUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.claude_computer_use import (
    ClaudeComputerUseManager as SyncClaudeComputerUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.cua import (
    CuaManager as SyncCuaManager,
)
from hyperbrowser.client.managers.sync_manager.agents.gemini_computer_use import (
    GeminiComputerUseManager as SyncGeminiComputerUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.hyper_agent import (
    HyperAgentManager as SyncHyperAgentManager,
)
from hyperbrowser.client.managers.sync_manager.crawl import (
    CrawlManager as SyncCrawlManager,
)
from hyperbrowser.client.managers.sync_manager.extract import (
    ExtractManager as SyncExtractManager,
)
from hyperbrowser.client.managers.sync_manager.scrape import (
    BatchScrapeManager as SyncBatchScrapeManager,
    ScrapeManager as SyncScrapeManager,
)
from hyperbrowser.client.managers.sync_manager.web.batch_fetch import (
    BatchFetchManager as SyncBatchFetchManager,
)
from hyperbrowser.client.managers.sync_manager.web.crawl import (
    WebCrawlManager as SyncWebCrawlManager,
)


def test_start_and_wait_methods_expose_max_status_failures():
    manager_methods = [
        SyncBrowserUseManager.start_and_wait,
        SyncCuaManager.start_and_wait,
        SyncClaudeComputerUseManager.start_and_wait,
        SyncGeminiComputerUseManager.start_and_wait,
        SyncHyperAgentManager.start_and_wait,
        SyncExtractManager.start_and_wait,
        SyncBatchScrapeManager.start_and_wait,
        SyncScrapeManager.start_and_wait,
        SyncCrawlManager.start_and_wait,
        SyncBatchFetchManager.start_and_wait,
        SyncWebCrawlManager.start_and_wait,
        AsyncBrowserUseManager.start_and_wait,
        AsyncCuaManager.start_and_wait,
        AsyncClaudeComputerUseManager.start_and_wait,
        AsyncGeminiComputerUseManager.start_and_wait,
        AsyncHyperAgentManager.start_and_wait,
        AsyncExtractManager.start_and_wait,
        AsyncBatchScrapeManager.start_and_wait,
        AsyncScrapeManager.start_and_wait,
        AsyncCrawlManager.start_and_wait,
        AsyncBatchFetchManager.start_and_wait,
        AsyncWebCrawlManager.start_and_wait,
    ]

    for method in manager_methods:
        signature = inspect.signature(method)
        assert "max_status_failures" in signature.parameters
