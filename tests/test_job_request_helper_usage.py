from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SYNC_MODULES = (
    "hyperbrowser/client/managers/sync_manager/extract.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/sync_manager/scrape.py",
)

ASYNC_MODULES = (
    "hyperbrowser/client/managers/async_manager/extract.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
)


def test_sync_job_managers_use_shared_request_helpers():
    for module_path in SYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "start_job(" in module_text
        assert "get_job_status(" in module_text
        assert "get_job(" in module_text
        assert "_client.transport.post(" not in module_text
        assert "_client.transport.get(" not in module_text
        assert "parse_response_model(" not in module_text


def test_async_job_managers_use_shared_request_helpers():
    for module_path in ASYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "start_job_async(" in module_text
        assert "get_job_status_async(" in module_text
        assert "get_job_async(" in module_text
        assert "_client.transport.post(" not in module_text
        assert "_client.transport.get(" not in module_text
        assert "parse_response_model(" not in module_text
