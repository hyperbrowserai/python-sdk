from typing import get_args

from hyperbrowser.models.consts import BrowserUseLlm
from hyperbrowser.tools.schema import (
    BROWSER_USE_LLM_SCHEMA,
    BROWSER_USE_SCHEMA,
    CRAWL_SCHEMA,
    EXTRACT_SCHEMA,
    SCRAPE_SCHEMA,
    SCREENSHOT_SCHEMA,
)


def test_browser_use_llm_schema_matches_sdk_literals():
    assert set(BROWSER_USE_LLM_SCHEMA["enum"]) == set(get_args(BrowserUseLlm))


def test_extract_schema_requires_only_urls():
    assert EXTRACT_SCHEMA["required"] == ["urls"]


def test_browser_use_schema_requires_only_task():
    assert BROWSER_USE_SCHEMA["required"] == ["task"]


def test_scrape_related_tool_schemas_require_only_url():
    assert SCRAPE_SCHEMA["required"] == ["url"]
    assert SCREENSHOT_SCHEMA["required"] == ["url"]
    assert CRAWL_SCHEMA["required"] == ["url"]
