from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


WEB_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/__init__.py",
    "hyperbrowser/client/managers/async_manager/web/__init__.py",
)

BATCH_FETCH_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
)

WEB_CRAWL_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_web_managers_use_shared_payload_helpers():
    for module_path in WEB_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_web_fetch_payload(" in module_text
        assert "build_web_search_payload(" in module_text
        assert "inject_web_output_schemas(" not in module_text
        assert "serialize_model_dump_to_dict(" not in module_text


def test_batch_fetch_managers_use_shared_start_payload_helper():
    for module_path in BATCH_FETCH_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_batch_fetch_start_payload(" in module_text
        assert "build_batch_fetch_get_params(" in module_text
        assert "initialize_paginated_job_response(" in module_text
        assert "inject_web_output_schemas(" not in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
        assert "BatchFetchJobResponse(" not in module_text


def test_web_crawl_managers_use_shared_start_payload_helper():
    for module_path in WEB_CRAWL_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_web_crawl_start_payload(" in module_text
        assert "build_web_crawl_get_params(" in module_text
        assert "initialize_paginated_job_response(" in module_text
        assert "inject_web_output_schemas(" not in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
        assert "WebCrawlJobResponse(" not in module_text
