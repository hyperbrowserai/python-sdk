from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_web_managers_use_shared_route_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "web_route_constants import" in module_text
        assert "_ROUTE_PREFIX = " in module_text
        assert '_ROUTE_PREFIX = "/web/' not in module_text
        assert "_build_url(self._ROUTE_PREFIX)" in module_text
        assert '_build_url("/web/' not in module_text
        assert '_build_url(f"/web/' not in module_text
