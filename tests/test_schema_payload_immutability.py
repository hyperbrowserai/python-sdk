from pydantic import BaseModel

from hyperbrowser.client.managers.sync_manager.agents.browser_use import (
    BrowserUseManager,
)
from hyperbrowser.client.managers.sync_manager.extract import ExtractManager
from hyperbrowser.client.managers.sync_manager.web import WebManager
from hyperbrowser.models import FetchOutputJson, FetchOutputOptions, FetchParams
from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams
from hyperbrowser.models.extract import StartExtractJobParams


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _RoutingTransport:
    def __init__(self):
        self.payloads = {}

    def post(self, url, data=None, files=None):
        self.payloads[url] = data
        if url.endswith("/task/browser-use"):
            return _FakeResponse({"jobId": "job_browser"})
        if url.endswith("/extract"):
            return _FakeResponse({"jobId": "job_extract"})
        if url.endswith("/web/fetch"):
            return _FakeResponse({"jobId": "job_fetch", "status": "completed"})
        raise AssertionError(f"Unexpected URL: {url}")


class _FakeClient:
    def __init__(self, transport):
        self.transport = transport

    def _build_url(self, path: str) -> str:
        return f"https://api.hyperbrowser.ai/api{path}"


class _OutputSchema(BaseModel):
    value: str


def test_extract_start_does_not_mutate_schema_param():
    transport = _RoutingTransport()
    manager = ExtractManager(_FakeClient(transport))
    params = StartExtractJobParams(urls=["https://example.com"], schema=_OutputSchema)

    manager.start(params)

    assert params.schema_ is _OutputSchema
    payload = next(v for k, v in transport.payloads.items() if k.endswith("/extract"))
    assert payload["schema"]["type"] == "object"
    assert "value" in payload["schema"]["properties"]


def test_browser_use_start_does_not_mutate_output_model_schema():
    transport = _RoutingTransport()
    manager = BrowserUseManager(_FakeClient(transport))
    params = StartBrowserUseTaskParams(
        task="open page", output_model_schema=_OutputSchema
    )

    manager.start(params)

    assert params.output_model_schema is _OutputSchema
    payload = next(
        v for k, v in transport.payloads.items() if k.endswith("/task/browser-use")
    )
    assert payload["outputModelSchema"]["type"] == "object"
    assert "value" in payload["outputModelSchema"]["properties"]


def test_web_fetch_does_not_mutate_json_output_schema():
    transport = _RoutingTransport()
    manager = WebManager(_FakeClient(transport))
    json_output = FetchOutputJson(type="json", schema=_OutputSchema)
    params = FetchParams(
        url="https://example.com",
        outputs=FetchOutputOptions(formats=[json_output]),
    )

    manager.fetch(params)

    assert json_output.schema_ is _OutputSchema
    payload = next(v for k, v in transport.payloads.items() if k.endswith("/web/fetch"))
    assert payload["outputs"]["formats"][0]["schema"]["type"] == "object"
    assert "value" in payload["outputs"]["formats"][0]["schema"]["properties"]
