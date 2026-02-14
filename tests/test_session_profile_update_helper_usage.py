from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SESSION_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
)


def test_session_managers_use_shared_profile_update_param_helper():
    for module_path in SESSION_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "resolve_update_profile_params(" in module_text
        assert "requires a plain UpdateSessionProfileParams object." not in module_text
        assert "Pass either UpdateSessionProfileParams as the second argument" not in module_text
        assert "Pass either a boolean as the second argument" not in module_text
