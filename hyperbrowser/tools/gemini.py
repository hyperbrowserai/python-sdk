"""Gemini function declarations for the Hyperbrowser tools.

The declarations are plain dicts that google-genai accepts, for example
``types.Tool(function_declarations=[FILL_CREDENTIAL_TOOL_GEMINI])``. Gemini
schemas are a subset of OpenAPI: they have no ``additionalProperties`` and
mark optional values with ``nullable`` instead of a ``"null"`` type.
"""

from copy import deepcopy
from typing import Any, Dict, Mapping

from typing_extensions import Required, TypeAlias, TypedDict

from hyperbrowser.tools.openai import (
    BROWSER_USE_TOOL_OPENAI,
    CRAWL_TOOL_OPENAI,
    EXTRACT_TOOL_OPENAI,
    FILL_CREDENTIAL_TOOL_OPENAI,
    SCRAPE_TOOL_OPENAI,
    SCREENSHOT_TOOL_OPENAI,
    ChatCompletionToolParam,
)

GeminiSchema: TypeAlias = Dict[str, object]


class FunctionDeclaration(TypedDict, total=False):
    name: Required[str]
    """The function's name: letters, digits, underscores, dots and dashes,
    at most 64 characters."""

    description: str
    """What the function does and when the model should call it."""

    parameters: GeminiSchema
    """The function's parameters as a Gemini (OpenAPI subset) schema."""


# Schema members Gemini understands, with google-genai's camelCase names.
_GEMINI_SCHEMA_KEYS = frozenset(
    {
        "default",
        "description",
        "enum",
        "example",
        "format",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "nullable",
        "pattern",
        "propertyOrdering",
        "required",
        "title",
    }
)


def to_gemini_schema(schema: Mapping[str, Any]) -> GeminiSchema:
    """Convert a tool's JSON schema to the Gemini form.

    ``"type": [T, "null"]`` becomes ``"type": T, "nullable": True``;
    ``additionalProperties`` and members Gemini doesn't know are dropped.
    """
    converted: GeminiSchema = {}
    for key, value in schema.items():
        if key == "type":
            if isinstance(value, (list, tuple)):
                types = [item for item in value if item != "null"]
                if len(types) != 1:
                    raise ValueError(
                        f"Gemini schemas can't express the type union {list(value)}"
                    )
                if len(types) != len(value):
                    converted["nullable"] = True
                value = types[0]
            converted["type"] = value
        elif key == "properties":
            converted["properties"] = {
                name: to_gemini_schema(member) for name, member in value.items()
            }
        elif key == "items":
            converted["items"] = to_gemini_schema(value)
        elif key == "anyOf":
            converted["anyOf"] = [to_gemini_schema(member) for member in value]
        elif key in _GEMINI_SCHEMA_KEYS:
            converted[key] = deepcopy(value)
    return converted


def to_gemini_function_declaration(
    name: str, description: str, parameters: Mapping[str, Any]
) -> FunctionDeclaration:
    return {
        "name": name,
        "description": description,
        "parameters": to_gemini_schema(parameters),
    }


def _from_openai(tool: ChatCompletionToolParam) -> FunctionDeclaration:
    function = tool["function"]
    return to_gemini_function_declaration(
        function["name"], function["description"], function["parameters"]
    )


SCRAPE_TOOL_GEMINI = _from_openai(SCRAPE_TOOL_OPENAI)
SCREENSHOT_TOOL_GEMINI = _from_openai(SCREENSHOT_TOOL_OPENAI)
CRAWL_TOOL_GEMINI = _from_openai(CRAWL_TOOL_OPENAI)
EXTRACT_TOOL_GEMINI = _from_openai(EXTRACT_TOOL_OPENAI)
BROWSER_USE_TOOL_GEMINI = _from_openai(BROWSER_USE_TOOL_OPENAI)
FILL_CREDENTIAL_TOOL_GEMINI = _from_openai(FILL_CREDENTIAL_TOOL_OPENAI)
