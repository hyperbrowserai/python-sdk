from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/profile.py",
    "hyperbrowser/client/managers/async_manager/profile.py",
)


def test_profile_managers_use_shared_route_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "profile_route_constants import" in module_text
        assert "_ROUTE_PREFIX = " in module_text
        assert "_LIST_ROUTE_PATH = " in module_text
        assert '"/profile"' not in module_text
        assert '"/profiles"' not in module_text
