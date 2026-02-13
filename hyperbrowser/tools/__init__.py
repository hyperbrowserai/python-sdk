import json
from collections.abc import Mapping as MappingABC
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
_NON_OBJECT_CRAWL_PAGE_TYPES = (
    str,
    bytes,
    bytearray,
    memoryview,
    int,
    float,
    bool,
)


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
            parsed_schema = json.loads(schema_value)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Invalid JSON string provided for `schema` in extract tool params",
                original_error=exc,
            ) from exc
        if parsed_schema is not None and not isinstance(parsed_schema, MappingABC):
            raise HyperbrowserError(
                "Extract tool `schema` must decode to a JSON object"
            )
        normalized_params["schema"] = parsed_schema
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
            if not key.strip():
                raise HyperbrowserError("tool params keys must not be empty")
            if key != key.strip():
                raise HyperbrowserError(
                    "tool params keys must not contain leading or trailing whitespace"
                )
            if any(ord(character) < 32 or ord(character) == 127 for character in key):
                raise HyperbrowserError(
                    "tool params keys must not contain control characters"
                )
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


def _serialize_extract_tool_data(data: Any) -> str:
    if data is None:
        return ""
    try:
        return json.dumps(data)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to serialize extract tool response data",
            original_error=exc,
        ) from exc


def _read_tool_response_data(response: Any, *, tool_name: str) -> Any:
    if isinstance(response, MappingABC):
        try:
            has_data_field = "data" in response
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to inspect {tool_name} response data field",
                original_error=exc,
            ) from exc
        if not has_data_field:
            raise HyperbrowserError(f"{tool_name} response must include 'data'")
        try:
            return response["data"]
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response data",
                original_error=exc,
            ) from exc
    try:
        return response.data
    except AttributeError:
        raise HyperbrowserError(f"{tool_name} response must include 'data'")
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to read {tool_name} response data",
            original_error=exc,
        ) from exc


def _read_optional_tool_response_field(
    response_data: Any,
    *,
    tool_name: str,
    field_name: str,
) -> str:
    if response_data is None:
        return ""
    if isinstance(response_data, MappingABC):
        try:
            field_value = response_data[field_name]
        except KeyError:
            return ""
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response field '{field_name}'",
                original_error=exc,
            ) from exc
    else:
        try:
            field_value = getattr(response_data, field_name)
        except AttributeError:
            return ""
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response field '{field_name}'",
                original_error=exc,
            ) from exc
    if field_value is None:
        return ""
    if not isinstance(field_value, str):
        raise HyperbrowserError(
            f"{tool_name} response field '{field_name}' must be a string"
        )
    return field_value


def _read_crawl_page_field(page: Any, *, field_name: str, page_index: int) -> Any:
    if isinstance(page, MappingABC):
        try:
            return page[field_name]
        except KeyError:
            return None
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read crawl tool page field '{field_name}' at index {page_index}",
                original_error=exc,
            ) from exc
    try:
        return getattr(page, field_name)
    except AttributeError:
        return None
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"Failed to read crawl tool page field '{field_name}' at index {page_index}",
            original_error=exc,
        ) from exc


def _render_crawl_markdown_output(response_data: Any) -> str:
    if response_data is None:
        return ""
    if not isinstance(response_data, list):
        raise HyperbrowserError("crawl tool response data must be a list")
    try:
        crawl_pages = list(response_data)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to iterate crawl tool response data",
            original_error=exc,
        ) from exc
    markdown_sections: list[str] = []
    for index, page in enumerate(crawl_pages):
        if page is None or isinstance(page, _NON_OBJECT_CRAWL_PAGE_TYPES):
            raise HyperbrowserError(
                f"crawl tool page must be an object at index {index}"
            )
        page_markdown = _read_crawl_page_field(
            page, field_name="markdown", page_index=index
        )
        if page_markdown is None:
            continue
        if not isinstance(page_markdown, str):
            raise HyperbrowserError(
                f"crawl tool page field 'markdown' must be a string at index {index}"
            )
        if not page_markdown:
            continue
        page_url = _read_crawl_page_field(page, field_name="url", page_index=index)
        if page_url is None:
            page_url_display = "<unknown url>"
        elif not isinstance(page_url, str):
            raise HyperbrowserError(
                f"crawl tool page field 'url' must be a string at index {index}"
            )
        else:
            page_url_display = page_url if page_url.strip() else "<unknown url>"
        markdown_sections.append(
            f"\n{'-' * 50}\nUrl: {page_url_display}\nMarkdown:\n{page_markdown}\n"
        )
    return "".join(markdown_sections)


class WebsiteScrapeTool:
    openai_tool_definition = SCRAPE_TOOL_OPENAI
    anthropic_tool_definition = SCRAPE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return _read_optional_tool_response_field(
            _read_tool_response_data(resp, tool_name="scrape tool"),
            tool_name="scrape tool",
            field_name="markdown",
        )

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return _read_optional_tool_response_field(
            _read_tool_response_data(resp, tool_name="scrape tool"),
            tool_name="scrape tool",
            field_name="markdown",
        )


class WebsiteScreenshotTool:
    openai_tool_definition = SCREENSHOT_TOOL_OPENAI
    anthropic_tool_definition = SCREENSHOT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return _read_optional_tool_response_field(
            _read_tool_response_data(resp, tool_name="screenshot tool"),
            tool_name="screenshot tool",
            field_name="screenshot",
        )

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.scrape.start_and_wait(
            params=StartScrapeJobParams(**_to_param_dict(params))
        )
        return _read_optional_tool_response_field(
            _read_tool_response_data(resp, tool_name="screenshot tool"),
            tool_name="screenshot tool",
            field_name="screenshot",
        )


class WebsiteCrawlTool:
    openai_tool_definition = CRAWL_TOOL_OPENAI
    anthropic_tool_definition = CRAWL_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.crawl.start_and_wait(
            params=StartCrawlJobParams(**_to_param_dict(params))
        )
        return _render_crawl_markdown_output(
            _read_tool_response_data(resp, tool_name="crawl tool")
        )

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.crawl.start_and_wait(
            params=StartCrawlJobParams(**_to_param_dict(params))
        )
        return _render_crawl_markdown_output(
            _read_tool_response_data(resp, tool_name="crawl tool")
        )


class WebsiteExtractTool:
    openai_tool_definition = EXTRACT_TOOL_OPENAI
    anthropic_tool_definition = EXTRACT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        normalized_params = _prepare_extract_tool_params(params)
        resp = hb.extract.start_and_wait(
            params=StartExtractJobParams(**normalized_params)
        )
        return _serialize_extract_tool_data(
            _read_tool_response_data(resp, tool_name="extract tool")
        )

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        normalized_params = _prepare_extract_tool_params(params)
        resp = await hb.extract.start_and_wait(
            params=StartExtractJobParams(**normalized_params)
        )
        return _serialize_extract_tool_data(
            _read_tool_response_data(resp, tool_name="extract tool")
        )


class BrowserUseTool:
    openai_tool_definition = BROWSER_USE_TOOL_OPENAI
    anthropic_tool_definition = BROWSER_USE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: Mapping[str, Any]) -> str:
        resp = hb.agents.browser_use.start_and_wait(
            params=StartBrowserUseTaskParams(**_to_param_dict(params))
        )
        return _read_optional_tool_response_field(
            _read_tool_response_data(resp, tool_name="browser-use tool"),
            tool_name="browser-use tool",
            field_name="final_result",
        )

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: Mapping[str, Any]) -> str:
        resp = await hb.agents.browser_use.start_and_wait(
            params=StartBrowserUseTaskParams(**_to_param_dict(params))
        )
        return _read_optional_tool_response_field(
            _read_tool_response_data(resp, tool_name="browser-use tool"),
            tool_name="browser-use tool",
            field_name="final_result",
        )


__all__ = [
    "WebsiteScrapeTool",
    "WebsiteScreenshotTool",
    "WebsiteCrawlTool",
    "WebsiteExtractTool",
    "BrowserUseTool",
]
