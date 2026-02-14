from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


DIRECT_SERIALIZATION_HELPER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
    "hyperbrowser/client/managers/sync_manager/profile.py",
    "hyperbrowser/client/managers/async_manager/profile.py",
    "hyperbrowser/client/managers/job_query_params_utils.py",
    "hyperbrowser/client/managers/web_payload_utils.py",
)

QUERY_HELPER_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
)


def test_managers_use_default_serialization_helper_for_optional_query_params():
    for module_path in DIRECT_SERIALIZATION_HELPER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "serialize_model_dump_or_default(" in module_text
        assert "params_obj = params or " not in module_text


def test_scrape_and_crawl_managers_use_query_param_helpers():
    for module_path in QUERY_HELPER_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if module_path.endswith("scrape.py"):
            assert "build_batch_scrape_get_params(" in module_text
        else:
            assert "build_crawl_get_params(" in module_text
        assert "serialize_model_dump_or_default(" not in module_text
