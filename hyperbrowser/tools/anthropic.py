from typing import Dict, Union, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from hyperbrowser.tools.schema import (
    BROWSER_USE_SCHEMA,
    CRAWL_SCHEMA,
    EXTRACT_SCHEMA,
    SCRAPE_SCHEMA,
    SCREENSHOT_SCHEMA,
)


class CacheControlEphemeralParam(TypedDict, total=False):
    type: Required[Literal["ephemeral"]]


class InputSchemaTyped(TypedDict, total=False):
    type: Required[Literal["object"]]

    properties: Optional[object]


InputSchema: TypeAlias = Union[InputSchemaTyped, Dict[str, object]]


class ToolParam(TypedDict, total=False):
    input_schema: Required[InputSchema]
    """[JSON schema](https://json-schema.org/) for this tool's input.

    This defines the shape of the `input` that your tool accepts and that the model
    will produce.
    """

    name: Required[str]
    """Name of the tool.

    This is how the tool will be called by the model and in tool_use blocks.
    """

    cache_control: Optional[CacheControlEphemeralParam]

    description: str
    """Description of what this tool does.

    Tool descriptions should be as detailed as possible. The more information that
    the model has about what the tool is and how to use it, the better it will
    perform. You can use natural language descriptions to reinforce important
    aspects of the tool input JSON schema.
    """


SCRAPE_TOOL_ANTHROPIC: ToolParam = {
    "input_schema": SCRAPE_SCHEMA,
    "name": "scrape_webpage",
    "description": "Scrape content from a webpage and return the content in markdown format",
}

SCREENSHOT_TOOL_ANTHROPIC: ToolParam = {
    "input_schema": SCREENSHOT_SCHEMA,
    "name": "screenshot_webpage",
    "description": "Scrape content from a webpage and return the content in screenshot format",
}

CRAWL_TOOL_ANTHROPIC: ToolParam = {
    "input_schema": CRAWL_SCHEMA,
    "name": "crawl_website",
    "description": "Crawl a website and return the content in markdown format",
}

EXTRACT_TOOL_ANTHROPIC: ToolParam = {
    "input_schema": EXTRACT_SCHEMA,
    "name": "extract_data",
    "description": "Extract data in a structured format from multiple URLs in a single function call. IMPORTANT: When information must be gathered from multiple sources (such as comparing items, researching topics across sites, or answering questions that span multiple webpages), ALWAYS include all relevant URLs in ONE function call. This enables comprehensive answers with cross-referenced information. Returns data as a json string.",
}

BROWSER_USE_TOOL_ANTHROPIC: ToolParam = {
    "input_schema": BROWSER_USE_SCHEMA,
    "name": "browser_use",
    "description": "Have an AI agent use a browser to perform a task on the web.",
}
