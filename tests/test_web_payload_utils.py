import pytest

import hyperbrowser.client.managers.web_payload_utils as web_payload_utils
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    FetchOutputOptions,
    FetchParams,
    GetBatchFetchJobParams,
    GetWebCrawlJobParams,
    StartBatchFetchJobParams,
    StartWebCrawlJobParams,
    WebSearchParams,
)


def test_build_web_fetch_payload_returns_serialized_payload():
    payload = web_payload_utils.build_web_fetch_payload(
        FetchParams(url="https://example.com")
    )

    assert payload["url"] == "https://example.com"


def test_build_web_fetch_payload_invokes_schema_injection(monkeypatch: pytest.MonkeyPatch):
    captured = {"payload": None, "formats": None}

    def _capture(payload, formats):
        captured["payload"] = payload
        captured["formats"] = formats

    monkeypatch.setattr(web_payload_utils, "inject_web_output_schemas", _capture)

    payload = web_payload_utils.build_web_fetch_payload(
        FetchParams(
            url="https://example.com",
            outputs=FetchOutputOptions(formats=["markdown"]),
        )
    )

    assert captured["payload"] is payload
    assert captured["formats"] == ["markdown"]


def test_build_web_search_payload_returns_serialized_payload():
    payload = web_payload_utils.build_web_search_payload(
        WebSearchParams(query="hyperbrowser sdk")
    )

    assert payload["query"] == "hyperbrowser sdk"


def test_build_batch_fetch_start_payload_returns_serialized_payload():
    payload = web_payload_utils.build_batch_fetch_start_payload(
        StartBatchFetchJobParams(urls=["https://example.com"])
    )

    assert payload["urls"] == ["https://example.com"]


def test_build_batch_fetch_start_payload_invokes_schema_injection(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {"payload": None, "formats": None}

    def _capture(payload, formats):
        captured["payload"] = payload
        captured["formats"] = formats

    monkeypatch.setattr(web_payload_utils, "inject_web_output_schemas", _capture)

    payload = web_payload_utils.build_batch_fetch_start_payload(
        StartBatchFetchJobParams(
            urls=["https://example.com"],
            outputs=FetchOutputOptions(formats=["markdown"]),
        )
    )

    assert captured["payload"] is payload
    assert captured["formats"] == ["markdown"]


def test_build_web_crawl_start_payload_returns_serialized_payload():
    payload = web_payload_utils.build_web_crawl_start_payload(
        StartWebCrawlJobParams(url="https://example.com")
    )

    assert payload["url"] == "https://example.com"


def test_build_batch_fetch_get_params_returns_serialized_payload():
    payload = web_payload_utils.build_batch_fetch_get_params(
        GetBatchFetchJobParams(page=2, batch_size=50)
    )

    assert payload == {"page": 2, "batchSize": 50}


def test_build_batch_fetch_get_params_uses_default_params():
    payload = web_payload_utils.build_batch_fetch_get_params()

    assert payload == {}


def test_build_web_crawl_get_params_returns_serialized_payload():
    payload = web_payload_utils.build_web_crawl_get_params(
        GetWebCrawlJobParams(page=3, batch_size=25)
    )

    assert payload == {"page": 3, "batchSize": 25}


def test_build_web_crawl_get_params_uses_default_params():
    payload = web_payload_utils.build_web_crawl_get_params()

    assert payload == {}


def test_build_web_crawl_start_payload_invokes_schema_injection(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {"payload": None, "formats": None}

    def _capture(payload, formats):
        captured["payload"] = payload
        captured["formats"] = formats

    monkeypatch.setattr(web_payload_utils, "inject_web_output_schemas", _capture)

    payload = web_payload_utils.build_web_crawl_start_payload(
        StartWebCrawlJobParams(
            url="https://example.com",
            outputs=FetchOutputOptions(formats=["markdown"]),
        )
    )

    assert captured["payload"] is payload
    assert captured["formats"] == ["markdown"]


def test_build_web_fetch_payload_wraps_runtime_model_dump_failures():
    class _BrokenFetchParams:
        outputs = None

        def model_dump(self, **kwargs):  # noqa: ARG002
            raise RuntimeError("boom")

    with pytest.raises(HyperbrowserError, match="Failed to serialize web fetch params") as exc_info:
        web_payload_utils.build_web_fetch_payload(_BrokenFetchParams())  # type: ignore[arg-type]

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_web_search_payload_preserves_hyperbrowser_model_dump_failures():
    class _BrokenSearchParams:
        def model_dump(self, **kwargs):  # noqa: ARG002
            raise HyperbrowserError("custom dump failure")

    with pytest.raises(HyperbrowserError, match="custom dump failure") as exc_info:
        web_payload_utils.build_web_search_payload(_BrokenSearchParams())  # type: ignore[arg-type]

    assert exc_info.value.original_error is None


def test_build_batch_fetch_start_payload_wraps_runtime_model_dump_failures():
    class _BrokenBatchFetchParams:
        outputs = None

        def model_dump(self, **kwargs):  # noqa: ARG002
            raise RuntimeError("boom")

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize batch fetch start params"
    ) as exc_info:
        web_payload_utils.build_batch_fetch_start_payload(_BrokenBatchFetchParams())  # type: ignore[arg-type]

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_web_crawl_start_payload_preserves_hyperbrowser_model_dump_failures():
    class _BrokenWebCrawlParams:
        def model_dump(self, **kwargs):  # noqa: ARG002
            raise HyperbrowserError("custom dump failure")

    with pytest.raises(HyperbrowserError, match="custom dump failure") as exc_info:
        web_payload_utils.build_web_crawl_start_payload(_BrokenWebCrawlParams())  # type: ignore[arg-type]

    assert exc_info.value.original_error is None


def test_build_batch_fetch_get_params_wraps_runtime_model_dump_failures():
    class _BrokenBatchFetchGetParams:
        def model_dump(self, **kwargs):  # noqa: ARG002
            raise RuntimeError("boom")

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize batch fetch get params"
    ) as exc_info:
        web_payload_utils.build_batch_fetch_get_params(_BrokenBatchFetchGetParams())  # type: ignore[arg-type]

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_web_crawl_get_params_preserves_hyperbrowser_model_dump_failures():
    class _BrokenWebCrawlGetParams:
        def model_dump(self, **kwargs):  # noqa: ARG002
            raise HyperbrowserError("custom dump failure")

    with pytest.raises(HyperbrowserError, match="custom dump failure") as exc_info:
        web_payload_utils.build_web_crawl_get_params(_BrokenWebCrawlGetParams())  # type: ignore[arg-type]

    assert exc_info.value.original_error is None
