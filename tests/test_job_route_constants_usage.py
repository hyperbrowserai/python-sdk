from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/extract.py",
    "hyperbrowser/client/managers/async_manager/extract.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
)


def test_job_managers_use_shared_route_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "job_route_constants import" in module_text
        assert "_ROUTE_PREFIX = " in module_text
        assert '_build_url("/scrape' not in module_text
        assert '_build_url(f"/scrape' not in module_text
        assert '_build_url("/crawl' not in module_text
        assert '_build_url(f"/crawl' not in module_text
        assert '_build_url("/extract' not in module_text
        assert '_build_url(f"/extract' not in module_text
