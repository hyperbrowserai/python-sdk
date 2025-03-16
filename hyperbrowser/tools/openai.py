from typing import Dict, Optional
from typing_extensions import Literal, Required, TypedDict, TypeAlias

from hyperbrowser.tools.schema import (
    BROWSER_USE_SCHEMA,
    CRAWL_SCHEMA,
    EXTRACT_SCHEMA,
    SCRAPE_SCHEMA,
    SCREENSHOT_SCHEMA,
)

FunctionParameters: TypeAlias = Dict[str, object]


class FunctionDefinition(TypedDict, total=False):
    name: Required[str]
    """The name of the function to be called.

    Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length
    of 64.
    """

    description: str
    """
    A description of what the function does, used by the model to choose when and
    how to call the function.
    """

    parameters: FunctionParameters
    """The parameters the functions accepts, described as a JSON Schema object.

    See the [guide](https://platform.openai.com/docs/guides/function-calling) for
    examples, and the
    [JSON Schema reference](https://json-schema.org/understanding-json-schema/) for
    documentation about the format.

    Omitting `parameters` defines a function with an empty parameter list.
    """

    strict: Optional[bool]
    """Whether to enable strict schema adherence when generating the function call.

    If set to true, the model will follow the exact schema defined in the
    `parameters` field. Only a subset of JSON Schema is supported when `strict` is
    `true`. Learn more about Structured Outputs in the
    [function calling guide](docs/guides/function-calling).
    """


class ChatCompletionToolParam(TypedDict, total=False):
    function: Required[FunctionDefinition]

    type: Required[Literal["function"]]
    """The type of the tool. Currently, only `function` is supported."""


SCRAPE_TOOL_OPENAI: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "scrape_webpage",
        "description": "Scrape content from a webpage and return the content in markdown format",
        "parameters": SCRAPE_SCHEMA,
        "strict": True,
    },
}

SCREENSHOT_TOOL_OPENAI: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "screenshot_webpage",
        "description": "Scrape content from a webpage and return the content in screenshot format",
        "parameters": SCREENSHOT_SCHEMA,
        "strict": True,
    },
}

CRAWL_TOOL_OPENAI: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "crawl_website",
        "description": "Crawl a website and return the content in markdown format",
        "parameters": CRAWL_SCHEMA,
        "strict": True,
    },
}

EXTRACT_TOOL_OPENAI: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "extract_data",
        "description": "Extract data in a structured format from multiple URLs in a single function call. IMPORTANT: When information must be gathered from multiple sources (such as comparing items, researching topics across sites, or answering questions that span multiple webpages), ALWAYS include all relevant URLs in ONE function call. This enables comprehensive answers with cross-referenced information. Returns data as a json string.",
        "parameters": EXTRACT_SCHEMA,
        "strict": True,
    },
}

BROWSER_USE_TOOL_OPENAI: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "browser_use",
        "description": "Have an AI agent use a browser to perform a task on the web.",
        "parameters": BROWSER_USE_SCHEMA,
        "strict": True,
    },
}
