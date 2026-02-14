from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.job_query_params_utils import (
    build_batch_scrape_get_params,
    build_crawl_get_params,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.crawl import GetCrawlJobParams
from hyperbrowser.models.scrape import GetBatchScrapeJobParams


def test_build_batch_scrape_get_params_uses_default_params_model():
    assert build_batch_scrape_get_params() == {}


def test_build_batch_scrape_get_params_serializes_given_params():
    payload = build_batch_scrape_get_params(
        GetBatchScrapeJobParams(page=2, batch_size=5)
    )

    assert payload == {"page": 2, "batchSize": 5}


def test_build_crawl_get_params_uses_default_params_model():
    assert build_crawl_get_params() == {}


def test_build_crawl_get_params_serializes_given_params():
    payload = build_crawl_get_params(GetCrawlJobParams(page=3, batch_size=8))

    assert payload == {"page": 3, "batchSize": 8}


def test_build_batch_scrape_get_params_wraps_runtime_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = GetBatchScrapeJobParams(page=1, batch_size=1)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(GetBatchScrapeJobParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize batch scrape get params"
    ) as exc_info:
        build_batch_scrape_get_params(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_crawl_get_params_rejects_non_dict_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    params = GetCrawlJobParams(page=1, batch_size=1)
    monkeypatch.setattr(
        GetCrawlJobParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"page": 1, "batchSize": 1}),
    )

    with pytest.raises(HyperbrowserError, match="Failed to serialize crawl get params"):
        build_crawl_get_params(params)
