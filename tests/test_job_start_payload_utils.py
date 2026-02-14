from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.job_start_payload_utils import (
    build_batch_scrape_start_payload,
    build_crawl_start_payload,
    build_scrape_start_payload,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.crawl import StartCrawlJobParams
from hyperbrowser.models.scrape import StartBatchScrapeJobParams, StartScrapeJobParams


def test_build_scrape_start_payload_serializes_model() -> None:
    payload = build_scrape_start_payload(StartScrapeJobParams(url="https://example.com"))

    assert payload == {"url": "https://example.com"}


def test_build_batch_scrape_start_payload_serializes_model() -> None:
    payload = build_batch_scrape_start_payload(
        StartBatchScrapeJobParams(urls=["https://example.com"])
    )

    assert payload == {"urls": ["https://example.com"]}


def test_build_crawl_start_payload_serializes_model() -> None:
    payload = build_crawl_start_payload(
        StartCrawlJobParams(
            url="https://example.com",
            max_pages=5,
        )
    )

    assert payload["url"] == "https://example.com"
    assert payload["maxPages"] == 5


@pytest.mark.parametrize(
    ("builder", "params", "error_message"),
    (
        (
            build_scrape_start_payload,
            StartScrapeJobParams(url="https://example.com"),
            "Failed to serialize scrape start params",
        ),
        (
            build_batch_scrape_start_payload,
            StartBatchScrapeJobParams(urls=["https://example.com"]),
            "Failed to serialize batch scrape start params",
        ),
        (
            build_crawl_start_payload,
            StartCrawlJobParams(url="https://example.com"),
            "Failed to serialize crawl start params",
        ),
    ),
)
def test_job_start_payload_builders_wrap_runtime_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
    builder,
    params,
    error_message: str,
) -> None:
    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(type(params), "model_dump", _raise_model_dump_error)

    with pytest.raises(HyperbrowserError, match=error_message) as exc_info:
        builder(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize(
    ("builder", "params", "error_message"),
    (
        (
            build_scrape_start_payload,
            StartScrapeJobParams(url="https://example.com"),
            "Failed to serialize scrape start params",
        ),
        (
            build_batch_scrape_start_payload,
            StartBatchScrapeJobParams(urls=["https://example.com"]),
            "Failed to serialize batch scrape start params",
        ),
        (
            build_crawl_start_payload,
            StartCrawlJobParams(url="https://example.com"),
            "Failed to serialize crawl start params",
        ),
    ),
)
def test_job_start_payload_builders_reject_non_dict_model_dump_payloads(
    monkeypatch: pytest.MonkeyPatch,
    builder,
    params,
    error_message: str,
) -> None:
    monkeypatch.setattr(
        type(params),
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"value": 1}),
    )

    with pytest.raises(HyperbrowserError, match=error_message) as exc_info:
        builder(params)

    assert exc_info.value.original_error is None
