from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
)


def test_session_managers_use_shared_route_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "session_route_constants import" in module_text
        assert "build_session_route" in module_text
        assert "_ROUTE_PREFIX = " in module_text
        assert "_LIST_ROUTE_PATH = " in module_text
        assert '"/session"' not in module_text
        assert '"/sessions"' not in module_text
        assert '_build_url("/session' not in module_text
        assert '_build_url(f"/session' not in module_text
        assert 'f"{self._ROUTE_PREFIX}/' not in module_text
