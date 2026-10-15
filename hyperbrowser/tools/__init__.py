import json
from typing import Any, Dict, Mapping, cast

from hyperbrowser import Hyperbrowser, AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.credential import CredentialFillResult
from hyperbrowser.types import (
    StartBrowserUseTaskParams,
    StartCrawlJobParams,
    StartExtractJobParams,
    StartScrapeJobParams,
    WebsiteExtractToolParams,
)

from .openai import (
    BROWSER_USE_TOOL_OPENAI,
    EXTRACT_TOOL_OPENAI,
    FILL_CREDENTIAL_TOOL_OPENAI,
    SCRAPE_TOOL_OPENAI,
    SCREENSHOT_TOOL_OPENAI,
    CRAWL_TOOL_OPENAI,
)
from .anthropic import (
    BROWSER_USE_TOOL_ANTHROPIC,
    EXTRACT_TOOL_ANTHROPIC,
    FILL_CREDENTIAL_TOOL_ANTHROPIC,
    SCRAPE_TOOL_ANTHROPIC,
    SCREENSHOT_TOOL_ANTHROPIC,
    CRAWL_TOOL_ANTHROPIC,
)
from .gemini import FILL_CREDENTIAL_TOOL_GEMINI


class WebsiteScrapeTool:
    openai_tool_definition = SCRAPE_TOOL_OPENAI
    anthropic_tool_definition = SCRAPE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartScrapeJobParams) -> str:
        resp = hb.scrape.start_and_wait(params=params)
        return resp.data.markdown if resp.data and resp.data.markdown else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: StartScrapeJobParams
    ) -> str:
        resp = await hb.scrape.start_and_wait(params=params)
        return resp.data.markdown if resp.data and resp.data.markdown else ""


class WebsiteScreenshotTool:
    openai_tool_definition = SCREENSHOT_TOOL_OPENAI
    anthropic_tool_definition = SCREENSHOT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartScrapeJobParams) -> str:
        resp = hb.scrape.start_and_wait(params=params)
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: StartScrapeJobParams
    ) -> str:
        resp = await hb.scrape.start_and_wait(params=params)
        return resp.data.screenshot if resp.data and resp.data.screenshot else ""


class WebsiteCrawlTool:
    openai_tool_definition = CRAWL_TOOL_OPENAI
    anthropic_tool_definition = CRAWL_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartCrawlJobParams) -> str:
        resp = hb.crawl.start_and_wait(params=params)
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-' * 50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown

    @staticmethod
    async def async_runnable(hb: AsyncHyperbrowser, params: StartCrawlJobParams) -> str:
        resp = await hb.crawl.start_and_wait(params=params)
        markdown = ""
        if resp.data:
            for page in resp.data:
                if page.markdown:
                    markdown += (
                        f"\n{'-' * 50}\nUrl: {page.url}\nMarkdown:\n{page.markdown}\n"
                    )
        return markdown


def _normalize_extract_tool_params(
    params: WebsiteExtractToolParams,
) -> StartExtractJobParams:
    normalized_params = dict(params)
    schema = normalized_params.get("schema")
    if schema and isinstance(schema, str):
        normalized_params["schema"] = json.loads(schema)
    return cast(StartExtractJobParams, normalized_params)


class WebsiteExtractTool:
    openai_tool_definition = EXTRACT_TOOL_OPENAI
    anthropic_tool_definition = EXTRACT_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: WebsiteExtractToolParams) -> str:
        normalized_params = _normalize_extract_tool_params(params)
        resp = hb.extract.start_and_wait(params=normalized_params)
        return json.dumps(resp.data) if resp.data else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: WebsiteExtractToolParams
    ) -> str:
        normalized_params = _normalize_extract_tool_params(params)
        resp = await hb.extract.start_and_wait(params=normalized_params)
        return json.dumps(resp.data) if resp.data else ""


class BrowserUseTool:
    openai_tool_definition = BROWSER_USE_TOOL_OPENAI
    anthropic_tool_definition = BROWSER_USE_TOOL_ANTHROPIC

    @staticmethod
    def runnable(hb: Hyperbrowser, params: StartBrowserUseTaskParams) -> str:
        resp = hb.agents.browser_use.start_and_wait(params=params)
        return resp.data.final_result if resp.data and resp.data.final_result else ""

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, params: StartBrowserUseTaskParams
    ) -> str:
        resp = await hb.agents.browser_use.start_and_wait(params=params)
        return resp.data.final_result if resp.data and resp.data.final_result else ""


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _fill_credential_request(params: Any) -> Dict[str, Any]:
    """Map the model's tool input to a fill request; null means absent."""
    if not isinstance(params, Mapping):
        # Fails validation, so the model gets an invalid_request error.
        params = {}
    request: Dict[str, Any] = {}
    # Never one_password: a 1Password fill names the origins its values may
    # be typed on, and a model must not choose those. Apps call
    # sessions.credentials.fill() directly for 1Password.
    for key in ("credential", "vault"):
        if _present(params.get(key)):
            request[key] = params.get(key)
    fields = params.get("fields")
    if isinstance(fields, list):
        fields = [
            {key: value for key, value in entry.items() if _present(value)}
            if isinstance(entry, Mapping)
            else entry
            for entry in fields
        ]
    request["fields"] = fields
    for key, alias in (
        ("page_id", "pageId"),
        ("page_url", "pageUrl"),
        ("frame_url", "frameUrl"),
    ):
        value = params.get(key, params.get(alias))
        if _present(value):
            request[key] = value
    return request


def _fill_credential_result_text(result: CredentialFillResult) -> str:
    return json.dumps(
        result.model_dump(mode="json", by_alias=True, exclude_none=True),
        separators=(",", ":"),
    )


def _fill_credential_error_text(error: HyperbrowserError) -> str:
    details = error.details
    if error.status_code is not None and isinstance(details, dict):
        # API errors keep the whole response body; the model needs only the
        # details the server added, such as the candidate pages.
        details = details.get("details")
    return json.dumps(
        {
            "error": {
                "code": error.code,
                "message": error.args[0] if error.args else str(error),
                "retryable": error.retryable,
                "details": details,
            }
        },
        separators=(",", ":"),
        default=str,
    )


class CredentialFillTool:
    """Let a model fill a stored secret, or a vault's entries, into a browser
    session.

    The model chooses the secret or vault by name and the inputs to fill; it
    never sees the values. The application binds the session::

        result = CredentialFillTool.runnable(hb, session.id, tool_input)

    The result is JSON text for the model. API and validation errors are
    returned as ``{"error": {"code", "message", "retryable", "details"}}``
    instead of raised, so the model can react; other exceptions propagate.

    1Password fills aren't offered: their request names the allowed origins,
    which a model shouldn't choose. Call ``sessions.credentials.fill()`` with
    ``one_password`` directly.
    """

    openai_tool_definition = FILL_CREDENTIAL_TOOL_OPENAI
    anthropic_tool_definition = FILL_CREDENTIAL_TOOL_ANTHROPIC
    gemini_tool_definition = FILL_CREDENTIAL_TOOL_GEMINI

    @staticmethod
    def runnable(hb: Hyperbrowser, session_id: str, params: Mapping[str, Any]) -> str:
        try:
            result = hb.sessions.credentials.fill(
                session_id, cast(Any, _fill_credential_request(params))
            )
        except HyperbrowserError as error:
            return _fill_credential_error_text(error)
        return _fill_credential_result_text(result)

    @staticmethod
    async def async_runnable(
        hb: AsyncHyperbrowser, session_id: str, params: Mapping[str, Any]
    ) -> str:
        try:
            result = await hb.sessions.credentials.fill(
                session_id, cast(Any, _fill_credential_request(params))
            )
        except HyperbrowserError as error:
            return _fill_credential_error_text(error)
        return _fill_credential_result_text(result)


__all__ = [
    "CredentialFillTool",
    "WebsiteScrapeTool",
    "WebsiteScreenshotTool",
    "WebsiteCrawlTool",
    "WebsiteExtractTool",
    "WebsiteExtractToolParams",
    "BrowserUseTool",
]
