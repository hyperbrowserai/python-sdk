from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


BATCH_JOB_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
)


def test_job_managers_use_shared_pagination_helpers():
    for module_path in BATCH_JOB_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "initialize_job_paginated_response(" in module_text
        assert "merge_job_paginated_page_response(" in module_text
        assert "total_page_batches = page_response.total_page_batches" not in module_text
        assert "job_response = BatchScrapeJobResponse(" not in module_text
        assert "job_response = CrawlJobResponse(" not in module_text
