from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "hyperbrowser/client/managers/async_manager/extension.py",
)


def test_extension_managers_use_shared_route_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "extension_route_constants import" in module_text
        assert "_CREATE_ROUTE_PATH = " in module_text
        assert "_LIST_ROUTE_PATH = " in module_text
        assert '"/extensions/add"' not in module_text
        assert '"/extensions/list"' not in module_text
