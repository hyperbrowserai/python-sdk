import json
from typing import Any, Dict, Mapping

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams
from hyperbrowser.models.crawl import StartCrawlJobParams
from hyperbrowser.models.extract import StartExtractJobParams
from hyperbrowser.models.scrape import StartScrapeJobParams
from hyperbrowser import Hyperbrowser, AsyncHyperbrowser

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


def _prepare_extract_tool_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    normalized_params: Dict[str, Any] = dict(params)
    schema_value = normalized_params.get("schema")
    if isinstance(schema_value, str):
        try:
            normalized_params["schema"] = json.loads(schema_value)
        except json.JSONDecodeError as exc:
            raise HyperbrowserError(
                "Invalid JSON string provided for `schema` in extract tool params",
                original_error=exc,
            ) from exc
    return normalized_params


class WebsiteScrapeTool:
    openai_tool_definition = SCRAPE_TOOL_OPENAI
    anthropic_tool_definition = SCRAPE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: dict) -> str:
        resp = hb.scrape.start_and_wait(params=StartScrapeJobParams(**params))
        return resp.data.markdown if resp.data and resp.data.markdown else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: dict) -> str:
        resp = await hb.scrape.start_and_wait(params=StartScrapeJobParams(**params))
        return resp.data.markdown if resp.data and resp.data.markdown else ""


class WebsiteScreenshotTool:
    openai_tool_definition = SCREENSHOT_TOOL_OPENAI
    anthropic_tool_definition = SCREENSHOT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: dict) -> str:
        resp = hb.scrape.start_and_wait(params=StartScrapeJobParams(**params))
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: dict) -> str:
        resp = await hb.scrape.start_and_wait(params=StartScrapeJobParams(**params))
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""


class WebsiteCrawlTool:
    openai_tool_definition = CRAWL_TOOL_OPENAI
    anthropic_tool_definition = CRAWL_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: dict) -> str:
        resp = hb.crawl.start_and_wait(params=StartCrawlJobParams(**params))
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-'*50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: dict) -> str:
        resp = await hb.crawl.start_and_wait(params=StartCrawlJobParams(**params))
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-'*50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown


class WebsiteExtractTool:
    openai_tool_definition = EXTRACT_TOOL_OPENAI
    anthropic_tool_definition = EXTRACT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: dict) -> str:
        normalized_params = _prepare_extract_tool_params(params)
        resp = hb.extract.start_and_wait(
            params=StartExtractJobParams(**normalized_params)
        )
        return json.dumps(resp.data) if resp.data else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: dict) -> str:
        normalized_params = _prepare_extract_tool_params(params)
        resp = await hb.extract.start_and_wait(
            params=StartExtractJobParams(**normalized_params)
        )
        return json.dumps(resp.data) if resp.data else ""


class BrowserUseTool:
    openai_tool_definition = BROWSER_USE_TOOL_OPENAI
    anthropic_tool_definition = BROWSER_USE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: dict) -> str:
        resp = hb.agents.browser_use.start_and_wait(
            params=StartBrowserUseTaskParams(**params)
        )
        return resp.data.final_result if resp.data and resp.data.final_result else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: dict) -> str:
        resp = await hb.agents.browser_use.start_and_wait(
            params=StartBrowserUseTaskParams(**params)
        )
        return resp.data.final_result if resp.data and resp.data.final_result else ""


__all__ = [
    "WebsiteScrapeTool",
    "WebsiteScreenshotTool",
    "WebsiteCrawlTool",
    "WebsiteExtractTool",
    "BrowserUseTool",
]
