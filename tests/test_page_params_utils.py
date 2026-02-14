from hyperbrowser.client.managers.page_params_utils import (
    DEFAULT_PAGE_BATCH_SIZE,
    build_page_batch_params,
)
from hyperbrowser.models.crawl import GetCrawlJobParams
from hyperbrowser.models.scrape import GetBatchScrapeJobParams


def test_build_page_batch_params_uses_default_batch_size():
    params = build_page_batch_params(GetBatchScrapeJobParams, page=3)

    assert isinstance(params, GetBatchScrapeJobParams)
    assert params.page == 3
    assert params.batch_size == DEFAULT_PAGE_BATCH_SIZE


def test_build_page_batch_params_accepts_custom_batch_size():
    params = build_page_batch_params(GetCrawlJobParams, page=2, batch_size=25)

    assert isinstance(params, GetCrawlJobParams)
    assert params.page == 2
    assert params.batch_size == 25
