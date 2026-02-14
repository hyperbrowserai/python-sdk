from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/computer_action.py",
    "hyperbrowser/client/managers/async_manager/computer_action.py",
)


def test_computer_action_managers_use_shared_operation_metadata():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "computer_action_operation_metadata import" in module_text
        assert "_OPERATION_METADATA = " in module_text
        assert "operation_name=self._OPERATION_METADATA." in module_text
        assert 'operation_name="computer action"' not in module_text
