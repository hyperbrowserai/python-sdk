from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/sync_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/cua.py",
    "hyperbrowser/client/managers/async_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/async_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/async_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/cua.py",
)


def test_agent_managers_use_shared_operation_metadata():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "agent_operation_metadata import" in module_text
        assert "_OPERATION_METADATA = " in module_text
        assert "operation_name=self._OPERATION_METADATA." in module_text
        assert "start_error_message=self._OPERATION_METADATA." in module_text
        assert "operation_name_prefix=self._OPERATION_METADATA." in module_text
        if "build_agent_start_payload(" in module_text:
            assert (
                "error_message=self._OPERATION_METADATA.start_payload_error_message"
                in module_text
            )
        assert 'operation_name="' not in module_text
        assert 'start_error_message="' not in module_text
        assert 'operation_name_prefix="' not in module_text
