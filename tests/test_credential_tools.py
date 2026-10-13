"""The fill_credential LLM tool and the Gemini tool declarations."""

import json

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.tools import (
    BrowserUseTool,
    CredentialFillTool,
    WebsiteCrawlTool,
    WebsiteExtractTool,
    WebsiteScrapeTool,
    WebsiteScreenshotTool,
)
from hyperbrowser.tools.gemini import to_gemini_schema
from tests.test_credentials import FIELDS, FILL_RESULT, mock_clients, respond


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def sdk(request):
    yield from mock_clients(request.param)


def _walk(schema):
    yield schema
    for member in schema.get("properties", {}).values():
        yield from _walk(member)
    if isinstance(schema.get("items"), dict):
        yield from _walk(schema["items"])


TOOLS = [
    WebsiteScrapeTool,
    WebsiteScreenshotTool,
    WebsiteCrawlTool,
    WebsiteExtractTool,
    BrowserUseTool,
    CredentialFillTool,
]


def test_fill_credential_tool_definitions():
    openai_tool = CredentialFillTool.openai_tool_definition
    anthropic_tool = CredentialFillTool.anthropic_tool_definition
    gemini_tool = CredentialFillTool.gemini_tool_definition
    function = openai_tool["function"]

    assert openai_tool["type"] == "function"
    assert function["name"] == "fill_credential"
    assert function["strict"] is True
    assert anthropic_tool["name"] == gemini_tool["name"] == "fill_credential"
    assert anthropic_tool["input_schema"] is function["parameters"]
    description = function["description"]
    assert anthropic_tool["description"] == gemini_tool["description"] == description
    for text in [
        "does NOT submit",
        "filled",
        "not_found",
        "ambiguous",
        "not_editable",
        "not_accepted",
        "not_populated",
        "CREDENTIAL_PAGE_AMBIGUOUS",
        "page_id",
    ]:
        assert text in description

    schema = function["parameters"]
    assert set(schema["properties"]) == {"credential", "fields", "page_id", "frame_url"}
    assert "session" not in json.dumps(schema).lower().replace("session's", "")
    fields = schema["properties"]["fields"]
    assert (fields["minItems"], fields["maxItems"]) == (1, 16)
    assert schema["properties"]["page_id"]["type"] == ["string", "null"]
    for member in _walk(schema):
        assert (
            member.get("description") or member is schema or member is fields["items"]
        )


@pytest.mark.parametrize("tool", TOOLS, ids=lambda tool: tool.__name__)
def test_openai_schemas_are_strict_mode_compatible(tool):
    for member in _walk(tool.openai_tool_definition["function"]["parameters"]):
        if member.get("type") == "object":
            assert member["additionalProperties"] is False
            assert set(member["required"]) == set(member["properties"])


@pytest.mark.parametrize("tool", TOOLS, ids=lambda tool: tool.__name__)
def test_gemini_declarations_use_the_openapi_subset(tool):
    declaration = tool.gemini_tool_definition
    assert declaration["name"] == tool.openai_tool_definition["function"]["name"]
    assert "additionalProperties" not in json.dumps(declaration)
    for member in _walk(declaration["parameters"]):
        assert isinstance(member["type"], str)


def test_gemini_schema_conversion():
    gemini = CredentialFillTool.gemini_tool_definition["parameters"]
    assert gemini["properties"]["page_id"]["type"] == "string"
    assert gemini["properties"]["page_id"]["nullable"] is True
    assert gemini["properties"]["frame_url"]["nullable"] is True
    assert "nullable" not in gemini["properties"]["credential"]
    assert gemini["properties"]["fields"]["maxItems"] == 16
    assert gemini["required"] == ["credential", "fields", "page_id", "frame_url"]

    with pytest.raises(ValueError, match="type union"):
        to_gemini_schema({"type": ["string", "number"]})
    assert to_gemini_schema({"type": "object", "$schema": "x", "anyOf": []}) == {
        "type": "object",
        "anyOf": [],
    }


TOOL_INPUT = {
    "credential": "github",
    "fields": FIELDS,
    "page_id": None,
    "frame_url": None,
}


def test_tool_runner_maps_model_input_and_returns_json(sdk):
    client, call, calls, outcomes = sdk
    runner = (
        CredentialFillTool.async_runnable
        if isinstance(client, AsyncHyperbrowser)
        else CredentialFillTool.runnable
    )
    respond(outcomes, FILL_RESULT)
    respond(outcomes, FILL_RESULT)

    text = call(runner, client, "session-1", TOOL_INPUT)
    assert json.loads(calls[0].content) == {"credential": "github", "fields": FIELDS}
    assert calls[0].url.path == "/api/session/session-1/credentials/fill"
    assert json.loads(text) == FILL_RESULT
    assert " " not in text.replace("https://", "")

    call(
        runner,
        client,
        "session-1",
        dict(TOOL_INPUT, page_id="PAGE2", frame_url="https://login.github.com/"),
    )
    assert json.loads(calls[1].content) == {
        "credential": "github",
        "fields": FIELDS,
        "pageId": "PAGE2",
        "frame": {"url": "https://login.github.com/"},
    }


def test_tool_runner_returns_errors_as_json(sdk):
    client, call, calls, outcomes = sdk
    runner = (
        CredentialFillTool.async_runnable
        if isinstance(client, AsyncHyperbrowser)
        else CredentialFillTool.runnable
    )
    pages = [{"pageId": "A", "url": "https://github.com/login", "title": "Sign in"}]
    respond(
        outcomes,
        {
            "code": "CREDENTIAL_PAGE_AMBIGUOUS",
            "message": "Several pages could be filled",
            "details": {"pages": pages},
        },
        409,
    )

    error = json.loads(call(runner, client, "s", TOOL_INPUT))
    assert error == {
        "error": {
            "code": "CREDENTIAL_PAGE_AMBIGUOUS",
            "message": "Several pages could be filled",
            "retryable": False,
            "details": {"pages": pages},
        }
    }

    error = json.loads(call(runner, client, "s", dict(TOOL_INPUT, fields=[])))
    assert error["error"]["code"] == "invalid_request"
    assert error["error"]["details"] is None
    assert len(calls) == 1


def test_tool_runner_lets_other_exceptions_propagate(monkeypatch):
    client = Hyperbrowser(api_key="test-key")

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(client.sessions.credentials, "fill", fail)
    with pytest.raises(RuntimeError):
        CredentialFillTool.runnable(client, "s", TOOL_INPUT)
    client.close()
