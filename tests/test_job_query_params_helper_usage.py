from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
)


def test_scrape_and_crawl_managers_use_shared_query_param_helpers():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if module_path.endswith("scrape.py"):
            assert "build_batch_scrape_get_params(" in module_text
        else:
            assert "build_crawl_get_params(" in module_text
        assert "serialize_model_dump_or_default(" not in module_text
