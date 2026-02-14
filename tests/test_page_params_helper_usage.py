from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_paginated_managers_use_shared_page_params_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_page_batch_params(" in module_text
        assert "batch_size=100" not in module_text
        assert "GetBatchScrapeJobParams(page=page" not in module_text
        assert "GetCrawlJobParams(page=page" not in module_text
        assert "GetBatchFetchJobParams(page=page" not in module_text
        assert "GetWebCrawlJobParams(page=page" not in module_text
