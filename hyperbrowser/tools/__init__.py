import json
from typing import cast

from hyperbrowser import Hyperbrowser, AsyncHyperbrowser
from hyperbrowser.types import (
    StartBrowserUseTaskParams,
    StartCrawlJobParams,
    StartExtractJobParams,
    StartScrapeJobParams,
    WebsiteExtractToolParams,
)

from .openai import (
    BROWSER_USE_TOOL_OPENAI,
    EXTRACT_TOOL_OPENAI,
    SCRAPE_TOOL_OPENAI,
    SCREENSHOT_TOOL_OPENAI,
    CRAWL_TOOL_OPENAI,
)
from .anthropic import (
    BROWSER_USE_TOOL_ANTHROPIC,
    EXTRACT_TOOL_ANTHROPIC,
    SCRAPE_TOOL_ANTHROPIC,
    SCREENSHOT_TOOL_ANTHROPIC,
    CRAWL_TOOL_ANTHROPIC,
)


class WebsiteScrapeTool:
    openai_tool_definition = SCRAPE_TOOL_OPENAI
    anthropic_tool_definition = SCRAPE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartScrapeJobParams) -> str:
        resp = hb.scrape.start_and_wait(params=params)
        return resp.data.markdown if resp.data and resp.data.markdown else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: StartScrapeJobParams
    ) -> str:
        resp = await hb.scrape.start_and_wait(params=params)
        return resp.data.markdown if resp.data and resp.data.markdown else ""


class WebsiteScreenshotTool:
    openai_tool_definition = SCREENSHOT_TOOL_OPENAI
    anthropic_tool_definition = SCREENSHOT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartScrapeJobParams) -> str:
        resp = hb.scrape.start_and_wait(params=params)
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: StartScrapeJobParams
    ) -> str:
        resp = await hb.scrape.start_and_wait(params=params)
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""


class WebsiteCrawlTool:
    openai_tool_definition = CRAWL_TOOL_OPENAI
    anthropic_tool_definition = CRAWL_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartCrawlJobParams) -> str:
        resp = hb.crawl.start_and_wait(params=params)
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-' * 50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: StartCrawlJobParams) -> str:
        resp = await hb.crawl.start_and_wait(params=params)
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-' * 50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown


def _normalize_extract_tool_params(
    params: WebsiteExtractToolParams,
) -> StartExtractJobParams:
    normalized_params = dict(params)
    schema = normalized_params.get("schema")
    if schema and isinstance(schema, str):
        normalized_params["schema"] = json.loads(schema)
    return cast(StartExtractJobParams, normalized_params)


class WebsiteExtractTool:
    openai_tool_definition = EXTRACT_TOOL_OPENAI
    anthropic_tool_definition = EXTRACT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: WebsiteExtractToolParams) -> str:
        normalized_params = _normalize_extract_tool_params(params)
        resp = hb.extract.start_and_wait(params=normalized_params)
        return json.dumps(resp.data) if resp.data else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: WebsiteExtractToolParams
    ) -> str:
        normalized_params = _normalize_extract_tool_params(params)
        resp = await hb.extract.start_and_wait(params=normalized_params)
        return json.dumps(resp.data) if resp.data else ""


class BrowserUseTool:
    openai_tool_definition = BROWSER_USE_TOOL_OPENAI
    anthropic_tool_definition = BROWSER_USE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartBrowserUseTaskParams) -> str:
        resp = hb.agents.browser_use.start_and_wait(params=params)
        return resp.data.final_result if resp.data and resp.data.final_result else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: StartBrowserUseTaskParams
    ) -> str:
        resp = await hb.agents.browser_use.start_and_wait(params=params)
        return resp.data.final_result if resp.data and resp.data.final_result else ""


__all__ = [
    "WebsiteScrapeTool",
    "WebsiteScreenshotTool",
    "WebsiteCrawlTool",
    "WebsiteExtractTool",
    "WebsiteExtractToolParams",
    "BrowserUseTool",
]
