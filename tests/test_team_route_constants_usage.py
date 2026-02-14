from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/team.py",
    "hyperbrowser/client/managers/async_manager/team.py",
)


def test_team_managers_use_shared_route_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "team_route_constants import" in module_text
        assert "_CREDIT_INFO_ROUTE_PATH = " in module_text
        assert '"/team/credit-info"' not in module_text
