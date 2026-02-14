from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SYNC_MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
)

ASYNC_MODULES = (
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_sync_web_managers_use_shared_request_helpers():
    for module_path in SYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "start_web_job(" in module_text
        assert "get_web_job_status(" in module_text
        assert "get_web_job(" in module_text
        assert "_client.transport.post(" not in module_text
        assert "_client.transport.get(" not in module_text
        assert "parse_response_model(" not in module_text


def test_async_web_managers_use_shared_request_helpers():
    for module_path in ASYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "start_web_job_async(" in module_text
        assert "get_web_job_status_async(" in module_text
        assert "get_web_job_async(" in module_text
        assert "_client.transport.post(" not in module_text
        assert "_client.transport.get(" not in module_text
        assert "parse_response_model(" not in module_text
