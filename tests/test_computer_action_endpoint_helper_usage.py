from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/computer_action.py",
    "hyperbrowser/client/managers/async_manager/computer_action.py",
)


def test_computer_action_managers_use_shared_endpoint_normalizer():
    for module_path in MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "normalize_computer_action_endpoint(" in module_text
        assert "session.computer_action_endpoint" not in module_text
        assert "computer_action_endpoint must be a string" not in module_text
        assert "computer_action_endpoint must not contain control characters" not in module_text
