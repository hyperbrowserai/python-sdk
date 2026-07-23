"""Tests for TypedDict / plain-dict params support and backward compat.

Managers accept either a Pydantic params instance (legacy) or a plain
dict / TypedDict (new ergonomic form). Both must produce byte-identical
wire payloads, and user-supplied JSON schemas must pass through untouched.
"""

import pytest

from pydantic import BaseModel

from hyperbrowser.models import (
    CreateSessionParams,
    StartScrapeJobParams,
    coerce_to_model,
)
from hyperbrowser.client.managers.sync_manager.scrape import ScrapeManager
from hyperbrowser.client.managers.async_manager.scrape import (
    ScrapeManager as AsyncScrapeManager,
)
from hyperbrowser.client.managers.sync_manager.extract import ExtractManager
from hyperbrowser.client.managers.sync_manager.session import SessionManager
from hyperbrowser.client.managers.sync_manager.web import WebManager


class _StopParsing(Exception):
    """Raised after a request is recorded to skip response-model parsing.

    These tests only assert on the outgoing wire payload, so we short-circuit
    before the manager tries to build a (schema-heavy) response object.
    """


class RecordingSyncTransport:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, files=None, timeout=None):
        self.calls.append({"method": "POST", "url": url, "data": data})
        raise _StopParsing

    def get(self, url, params=None, follow_redirects=False):
        self.calls.append({"method": "GET", "url": url, "params": params})
        raise _StopParsing


class RecordingAsyncTransport:
    def __init__(self):
        self.calls = []

    async def post(self, url, data=None, files=None, timeout=None):
        self.calls.append({"method": "POST", "url": url, "data": data})
        raise _StopParsing

    async def get(self, url, params=None, follow_redirects=False):
        self.calls.append({"method": "GET", "url": url, "params": params})
        raise _StopParsing


def _capture(fn):
    try:
        fn()
    except _StopParsing:
        pass


async def _capture_async(coro):
    try:
        await coro
    except _StopParsing:
        pass


class FakeSyncClient:
    def __init__(self):
        self.transport = RecordingSyncTransport()
        self.timeout = 30

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


class FakeAsyncClient:
    def __init__(self):
        self.transport = RecordingAsyncTransport()
        self.timeout = 30

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com{path}"


# --- coerce_to_model unit behavior ---------------------------------------


def test_coerce_dict_matches_pydantic_payload():
    payload = {
        "url": "https://example.com",
        "scrape_options": {
            "formats": ["markdown"],
            "only_main_content": True,
        },
        "session_options": {"use_stealth": True},
    }
    from_dict = coerce_to_model(StartScrapeJobParams, payload).model_dump(
        exclude_none=True, by_alias=True
    )
    from_model = StartScrapeJobParams(
        url="https://example.com",
        scrape_options={"formats": ["markdown"], "only_main_content": True},
        session_options=CreateSessionParams(use_stealth=True),
    ).model_dump(exclude_none=True, by_alias=True)
    assert from_dict == from_model
    # Nested camelCase aliases are applied for both forms.
    assert from_dict["scrapeOptions"]["onlyMainContent"] is True
    assert from_dict["sessionOptions"]["useStealth"] is True


def test_coerce_passes_through_model_instance():
    model = StartScrapeJobParams(url="https://example.com")
    assert coerce_to_model(StartScrapeJobParams, model) is model


def test_coerce_none_returns_empty_model():
    assert isinstance(coerce_to_model(CreateSessionParams, None), CreateSessionParams)


def test_coerce_rejects_wrong_model_type():
    with pytest.raises(TypeError):
        coerce_to_model(StartScrapeJobParams, CreateSessionParams())


# --- manager parity: dict vs Pydantic ------------------------------------


def test_sync_scrape_start_dict_matches_model():
    dict_client = FakeSyncClient()
    model_client = FakeSyncClient()

    payload = {
        "url": "https://example.com",
        "scrape_options": {"formats": ["markdown"]},
    }
    _capture(lambda: ScrapeManager(dict_client).start(payload))
    _capture(
        lambda: ScrapeManager(model_client).start(
            StartScrapeJobParams(
                url="https://example.com", scrape_options={"formats": ["markdown"]}
            )
        )
    )
    assert (
        dict_client.transport.calls[0]["data"]
        == (model_client.transport.calls[0]["data"])
    )
    assert dict_client.transport.calls[0]["data"] == {
        "url": "https://example.com",
        "scrapeOptions": {"formats": ["markdown"]},
    }


@pytest.mark.anyio
async def test_async_scrape_start_dict_matches_model():
    dict_client = FakeAsyncClient()
    model_client = FakeAsyncClient()

    payload = {
        "url": "https://example.com",
        "scrape_options": {"formats": ["markdown"]},
    }
    await _capture_async(AsyncScrapeManager(dict_client).start(payload))
    await _capture_async(
        AsyncScrapeManager(model_client).start(
            StartScrapeJobParams(
                url="https://example.com", scrape_options={"formats": ["markdown"]}
            )
        )
    )
    assert (
        dict_client.transport.calls[0]["data"]
        == (model_client.transport.calls[0]["data"])
    )


def test_sync_session_create_dict_matches_model():
    dict_client = FakeSyncClient()
    model_client = FakeSyncClient()

    _capture(
        lambda: SessionManager(dict_client).create(
            {"use_stealth": True, "use_proxy": True}
        )
    )
    _capture(
        lambda: SessionManager(model_client).create(
            CreateSessionParams(use_stealth=True, use_proxy=True)
        )
    )
    sent = dict_client.transport.calls[0]["data"]
    assert sent == model_client.transport.calls[0]["data"]
    assert sent["useStealth"] is True
    assert sent["useProxy"] is True


def test_sync_session_create_none_sends_empty_payload():
    client = FakeSyncClient()
    _capture(lambda: SessionManager(client).create())
    assert client.transport.calls[0]["data"] == {}


# --- user-supplied JSON schema pass-through -------------------------------


def test_extract_dict_schema_passthrough_not_camel_cased():
    client = FakeSyncClient()
    user_schema = {
        "type": "object",
        "properties": {"first_name": {"type": "string"}},
        "required": ["first_name"],
    }
    _capture(
        lambda: ExtractManager(client).start(
            {"urls": ["https://example.com"], "schema": user_schema}
        )
    )
    sent = client.transport.calls[0]["data"]
    # Arbitrary user schema keys must be preserved verbatim.
    assert sent["schema"] == user_schema


def test_extract_pydantic_schema_class_is_expanded():
    class Person(BaseModel):
        first_name: str

    client = FakeSyncClient()
    _capture(
        lambda: ExtractManager(client).start(
            {"urls": ["https://example.com"], "schema": Person}
        )
    )
    sent = client.transport.calls[0]["data"]
    assert sent["schema"]["type"] == "object"
    assert "first_name" in sent["schema"]["properties"]


def test_web_fetch_dict_matches_model():
    from hyperbrowser.models import FetchParams

    dict_client = FakeSyncClient()
    model_client = FakeSyncClient()

    _capture(lambda: WebManager(dict_client).fetch({"url": "https://example.com"}))
    _capture(
        lambda: WebManager(model_client).fetch(FetchParams(url="https://example.com"))
    )
    assert (
        dict_client.transport.calls[0]["data"]
        == (model_client.transport.calls[0]["data"])
    )
