from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SYNC_MODULES = (
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
)

ASYNC_MODULES = (
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_sync_managers_use_job_fetch_helpers_with_defaults():
    for module_path in SYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "fetch_job_result_with_defaults(" in module_text
        assert "collect_paginated_results_with_defaults(" in module_text
        assert "read_page_current_batch" in module_text
        assert "read_page_total_batches" in module_text
        assert "retry_operation(" not in module_text
        assert "collect_paginated_results(" not in module_text
        assert "build_fetch_operation_name(" not in module_text
        assert "get_current_page_batch=lambda page_response:" not in module_text
        assert "get_total_page_batches=lambda page_response:" not in module_text
        assert "max_attempts=POLLING_ATTEMPTS" not in module_text
        assert "retry_delay_seconds=0.5" not in module_text


def test_async_managers_use_job_fetch_helpers_with_defaults():
    for module_path in ASYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "fetch_job_result_with_defaults_async(" in module_text
        assert "collect_paginated_results_with_defaults_async(" in module_text
        assert "read_page_current_batch" in module_text
        assert "read_page_total_batches" in module_text
        assert "retry_operation_async(" not in module_text
        assert "collect_paginated_results_async(" not in module_text
        assert "build_fetch_operation_name(" not in module_text
        assert "get_current_page_batch=lambda page_response:" not in module_text
        assert "get_total_page_batches=lambda page_response:" not in module_text
        assert "max_attempts=POLLING_ATTEMPTS" not in module_text
        assert "retry_delay_seconds=0.5" not in module_text
