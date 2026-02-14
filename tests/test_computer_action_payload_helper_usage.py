from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/computer_action.py",
    "hyperbrowser/client/managers/async_manager/computer_action.py",
)


def test_computer_action_managers_use_shared_payload_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_computer_action_payload(" in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
