import pytest

from hyperbrowser.client.managers.page_params_utils import (
    DEFAULT_PAGE_BATCH_SIZE,
    build_page_batch_params,
)
from hyperbrowser.exceptions import HyperbrowserError
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


def test_build_page_batch_params_rejects_non_plain_int_page():
    with pytest.raises(HyperbrowserError, match="page must be a plain integer"):
        build_page_batch_params(GetBatchScrapeJobParams, page=True)  # type: ignore[arg-type]


def test_build_page_batch_params_rejects_non_positive_page():
    with pytest.raises(HyperbrowserError, match="page must be a positive integer"):
        build_page_batch_params(GetBatchScrapeJobParams, page=0)


def test_build_page_batch_params_rejects_non_plain_int_batch_size():
    class _IntSubclass(int):
        pass

    with pytest.raises(HyperbrowserError, match="batch_size must be a plain integer"):
        build_page_batch_params(
            GetBatchScrapeJobParams,
            page=1,
            batch_size=_IntSubclass(10),  # type: ignore[arg-type]
        )


def test_build_page_batch_params_rejects_non_positive_batch_size():
    with pytest.raises(HyperbrowserError, match="batch_size must be a positive integer"):
        build_page_batch_params(GetBatchScrapeJobParams, page=1, batch_size=0)


def test_build_page_batch_params_wraps_runtime_constructor_errors():
    class _BrokenParams:
        def __init__(self, *, page, batch_size):  # noqa: ARG002
            raise RuntimeError("boom")

    with pytest.raises(
        HyperbrowserError, match="Failed to build paginated page params"
    ) as exc_info:
        build_page_batch_params(_BrokenParams, page=1)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_page_batch_params_preserves_hyperbrowser_errors():
    class _BrokenParams:
        def __init__(self, *, page, batch_size):  # noqa: ARG002
            raise HyperbrowserError("custom failure")

    with pytest.raises(HyperbrowserError, match="custom failure") as exc_info:
        build_page_batch_params(_BrokenParams, page=1)

    assert exc_info.value.original_error is None


def test_build_page_batch_params_rejects_constructor_returning_wrong_type():
    class _BrokenParams:
        def __new__(cls, *, page, batch_size):  # noqa: ARG003
            return {"page": page, "batch_size": batch_size}

    with pytest.raises(
        HyperbrowserError,
        match="Paginated page params model constructor returned invalid type",
    ):
        build_page_batch_params(_BrokenParams, page=1)
