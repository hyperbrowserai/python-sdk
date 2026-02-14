import inspect
import json
from collections.abc import Mapping as MappingABC
from typing import Any, Dict, Mapping

from hyperbrowser.display_utils import format_string_key_for_error
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.mapping_utils import (
    copy_mapping_values_by_string_keys,
    read_string_mapping_keys,
)
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
_NON_OBJECT_CRAWL_PAGE_TYPES = (
    str,
    bytes,
    bytearray,
    memoryview,
    int,
    float,
    bool,
)


def _has_declared_attribute(
    value: Any, attribute_name: str, *, error_message: str
) -> bool:
    try:
        inspect.getattr_static(value, attribute_name)
        return True
    except AttributeError:
        return False
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(error_message, original_error=exc) from exc


def _format_tool_param_key_for_error(key: str) -> str:
    return format_string_key_for_error(key, max_length=_MAX_KEY_DISPLAY_LENGTH)


def _normalize_extract_schema_mapping(
    schema_value: MappingABC[object, Any],
) -> Dict[str, Any]:
    normalized_schema_keys = read_string_mapping_keys(
        schema_value,
        expected_mapping_error="Extract tool `schema` must be an object or JSON string",
        read_keys_error="Failed to read extract tool `schema` object keys",
        non_string_key_error_builder=lambda _key: (
            "Extract tool `schema` object keys must be strings"
        ),
    )
    return copy_mapping_values_by_string_keys(
        schema_value,
        normalized_schema_keys,
        read_value_error_builder=lambda key_display: (
            f"Failed to read extract tool `schema` value for key '{key_display}'"
        ),
        key_display=_format_tool_param_key_for_error,
    )


def _prepare_extract_tool_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    normalized_params = _to_param_dict(params)
    schema_value = normalized_params.get("schema")
    if schema_value is not None and not (
        type(schema_value) is str or isinstance(schema_value, MappingABC)
    ):
        raise HyperbrowserError(
            "Extract tool `schema` must be an object or JSON string"
        )
    if type(schema_value) is str:
        try:
            parsed_schema = json.loads(schema_value)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Invalid JSON string provided for `schema` in extract tool params",
                original_error=exc,
            ) from exc
        if not isinstance(parsed_schema, MappingABC):
            raise HyperbrowserError(
                "Extract tool `schema` must decode to a JSON object"
            )
        normalized_params["schema"] = _normalize_extract_schema_mapping(parsed_schema)
    elif isinstance(schema_value, MappingABC):
        normalized_params["schema"] = _normalize_extract_schema_mapping(schema_value)
    return normalized_params


def _to_param_dict(params: Mapping[str, Any]) -> Dict[str, Any]:
    param_keys = read_string_mapping_keys(
        params,
        expected_mapping_error="tool params must be a mapping",
        read_keys_error="Failed to read tool params keys",
        non_string_key_error_builder=lambda _key: "tool params keys must be strings",
    )
    for key in param_keys:
        try:
            normalized_key = key.strip()
            if type(normalized_key) is not str:
                raise TypeError("normalized tool param key must be a string")
            is_empty_key = len(normalized_key) == 0
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize tool param key",
                original_error=exc,
            ) from exc
        if is_empty_key:
            raise HyperbrowserError("tool params keys must not be empty")
        try:
            has_surrounding_whitespace = key != normalized_key
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize tool param key",
                original_error=exc,
            ) from exc
        if has_surrounding_whitespace:
            raise HyperbrowserError(
                "tool params keys must not contain leading or trailing whitespace"
            )
        try:
            contains_control_character = any(
                ord(character) < 32 or ord(character) == 127 for character in key
            )
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to validate tool param key characters",
                original_error=exc,
            ) from exc
        if contains_control_character:
            raise HyperbrowserError(
                "tool params keys must not contain control characters"
            )
    return copy_mapping_values_by_string_keys(
        params,
        param_keys,
        read_value_error_builder=lambda key_display: (
            f"Failed to read tool param '{key_display}'"
        ),
        key_display=_format_tool_param_key_for_error,
    )


def _serialize_extract_tool_data(data: Any) -> str:
    if data is None:
        return ""
    try:
        serialized_data = json.dumps(data, allow_nan=False)
        if type(serialized_data) is not str:
            raise TypeError("serialized extract tool response data must be a string")
        return serialized_data
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to serialize extract tool response data",
            original_error=exc,
        ) from exc


def _normalize_optional_text_field_value(
    field_value: Any,
    *,
    error_message: str,
) -> str:
    if field_value is None:
        return ""
    if type(field_value) is str:
        try:
            normalized_field_value = "".join(character for character in field_value)
            if type(normalized_field_value) is not str:
                raise TypeError("normalized text field must be a string")
            return normalized_field_value
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                error_message,
                original_error=exc,
            ) from exc
    if type(field_value) is not str and str in type(field_value).__mro__:
        raise HyperbrowserError(error_message)
    if isinstance(field_value, (bytes, bytearray, memoryview)):
        try:
            normalized_field_value = memoryview(field_value).tobytes().decode("utf-8")
            if type(normalized_field_value) is not str:
                raise TypeError("normalized text field must be a string")
            return normalized_field_value
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise HyperbrowserError(
                error_message,
                original_error=exc,
            ) from exc
    raise HyperbrowserError(error_message)


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
        except KeyError as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response data",
                original_error=exc,
            ) from exc
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response data",
                original_error=exc,
            ) from exc
    try:
        return response.data
    except AttributeError as exc:
        if _has_declared_attribute(
            response,
            "data",
            error_message=f"Failed to inspect {tool_name} response data field",
        ):
            raise HyperbrowserError(
                f"Failed to read {tool_name} response data",
                original_error=exc,
            ) from exc
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
            has_field = field_name in response_data
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to inspect {tool_name} response field '{field_name}'",
                original_error=exc,
            ) from exc
        if not has_field:
            return ""
        try:
            field_value = response_data[field_name]
        except HyperbrowserError:
            raise
        except KeyError as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response field '{field_name}'",
                original_error=exc,
            ) from exc
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read {tool_name} response field '{field_name}'",
                original_error=exc,
            ) from exc
    else:
        try:
            field_value = getattr(response_data, field_name)
        except AttributeError as exc:
            if _has_declared_attribute(
                response_data,
                field_name,
                error_message=(
                    f"Failed to inspect {tool_name} response field '{field_name}'"
                ),
            ):
                raise HyperbrowserError(
                    f"Failed to read {tool_name} response field '{field_name}'",
                    original_error=exc,
                ) from exc
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
    return _normalize_optional_text_field_value(
        field_value,
        error_message=(
            f"{tool_name} response field '{field_name}' must be a UTF-8 string"
        ),
    )


def _read_crawl_page_field(page: Any, *, field_name: str, page_index: int) -> Any:
    if isinstance(page, MappingABC):
        try:
            has_field = field_name in page
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to inspect crawl tool page field '{field_name}' at index {page_index}",
                original_error=exc,
            ) from exc
        if not has_field:
            return None
        try:
            return page[field_name]
        except HyperbrowserError:
            raise
        except KeyError as exc:
            raise HyperbrowserError(
                f"Failed to read crawl tool page field '{field_name}' at index {page_index}",
                original_error=exc,
            ) from exc
        except Exception as exc:
            raise HyperbrowserError(
                f"Failed to read crawl tool page field '{field_name}' at index {page_index}",
                original_error=exc,
            ) from exc
    try:
        return getattr(page, field_name)
    except AttributeError as exc:
        if _has_declared_attribute(
            page,
            field_name,
            error_message=(
                f"Failed to inspect crawl tool page field '{field_name}' at index {page_index}"
            ),
        ):
            raise HyperbrowserError(
                f"Failed to read crawl tool page field '{field_name}' at index {page_index}",
                original_error=exc,
            ) from exc
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
    if type(response_data) is not list:
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
        page_markdown = _normalize_optional_text_field_value(
            page_markdown,
            error_message=(
                "crawl tool page field 'markdown' must be a UTF-8 string "
                f"at index {index}"
            ),
        )
        if not page_markdown:
            continue
        page_url = _read_crawl_page_field(page, field_name="url", page_index=index)
        if page_url is None:
            page_url_display = "<unknown url>"
        else:
            page_url = _normalize_optional_text_field_value(
                page_url,
                error_message=(
                    f"crawl tool page field 'url' must be a UTF-8 string at index {index}"
                ),
            )
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
