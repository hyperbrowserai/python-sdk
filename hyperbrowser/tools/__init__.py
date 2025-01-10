from hyperbrowser.models.crawl import StartCrawlJobParams
from hyperbrowser.models.scrape import StartScrapeJobParams
from hyperbrowser import Hyperbrowser, AsyncHyperbrowser

from .openai import (
    SCRAPE_TOOL_OPENAI,
    CRAWL_TOOL_OPENAI,
)
from .anthropic import (
    SCRAPE_TOOL_ANTHROPIC,
    CRAWL_TOOL_ANTHROPIC,
)


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


__all__ = [
    "WebsiteScrapeTool",
    "WebsiteCrawlTool",
]
