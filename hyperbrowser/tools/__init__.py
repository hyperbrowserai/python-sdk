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

_MAX_KEY_DISPLAY_LENGTH = 120
_TRUNCATED_KEY_DISPLAY_SUFFIX = "... (truncated)"


def _format_tool_param_key_for_error(key: str) -> str:
    normalized_key = "".join(
        "?" if ord(character) < 32 or ord(character) == 127 else character
        for character in key
    ).strip()
    if not normalized_key:
        return "<blank key>"
    if len(normalized_key) <= _MAX_KEY_DISPLAY_LENGTH:
        return normalized_key
    available_length = _MAX_KEY_DISPLAY_LENGTH - len(_TRUNCATED_KEY_DISPLAY_SUFFIX)
    if available_length <= 0:
        return _TRUNCATED_KEY_DISPLAY_SUFFIX
    return f"{normalized_key[:available_length]}{_TRUNCATED_KEY_DISPLAY_SUFFIX}"


def _prepare_extract_tool_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    normalized_params = _to_param_dict(params)
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


def _to_param_dict(params: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(params, Mapping):
        raise HyperbrowserError("tool params must be a mapping")
    try:
        param_keys = list(params.keys())
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to read tool params keys",
            original_error=exc,
        ) from exc
    for key in param_keys:
        if isinstance(key, str):
            continue
        raise HyperbrowserError("tool params keys must be strings")
    normalized_params: Dict[str, Any] = {}
    for key in param_keys:
        try:
            normalized_params[key] = params[key]
        except HyperbrowserError:
            raise
        except Exception as exc:
            key_display = _format_tool_param_key_for_error(key)
            raise HyperbrowserError(
                f"Failed to read tool param '{key_display}'",
                original_error=exc,
            ) from exc
    return normalized_params


class WebsiteScrapeTool:
    openai_tool_definition = SCRAPE_TOOL_OPENAI
    anthropic_tool_definition = SCRAPE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return resp.data.markdown if resp.data and resp.data.markdown else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return resp.data.markdown if resp.data and resp.data.markdown else ""


class WebsiteScreenshotTool:
    openai_tool_definition = SCREENSHOT_TOOL_OPENAI
    anthropic_tool_definition = SCREENSHOT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""


class WebsiteCrawlTool:
    openai_tool_definition = CRAWL_TOOL_OPENAI
    anthropic_tool_definition = CRAWL_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.crawl.start_and_wait(
            params=StartCrawlJobParams(**_to_param_dict(params))
        )
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-' * 50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.crawl.start_and_wait(
            params=StartCrawlJobParams(**_to_param_dict(params))
        )
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-' * 50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown


class WebsiteExtractTool:
    openai_tool_definition = EXTRACT_TOOL_OPENAI
    anthropic_tool_definition = EXTRACT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        normalized_params = _prepare_extract_tool_params(params)
        resp = hb.extract.start_and_wait(
            params=StartExtractJobParams(**normalized_params)
        )
        return json.dumps(resp.data) if resp.data else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        normalized_params = _prepare_extract_tool_params(params)
        resp = await hb.extract.start_and_wait(
            params=StartExtractJobParams(**normalized_params)
        )
        return json.dumps(resp.data) if resp.data else ""


class BrowserUseTool:
    openai_tool_definition = BROWSER_USE_TOOL_OPENAI
    anthropic_tool_definition = BROWSER_USE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.agents.browser_use.start_and_wait(
            params=StartBrowserUseTaskParams(**_to_param_dict(params))
        )
        return resp.data.final_result if resp.data and resp.data.final_result else ""

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.agents.browser_use.start_and_wait(
            params=StartBrowserUseTaskParams(**_to_param_dict(params))
        )
        return resp.data.final_result if resp.data and resp.data.final_result else ""


__all__ = [
    "WebsiteScrapeTool",
    "WebsiteScreenshotTool",
    "WebsiteCrawlTool",
    "WebsiteExtractTool",
    "BrowserUseTool",
]
