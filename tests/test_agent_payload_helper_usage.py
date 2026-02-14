from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/async_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/sync_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/cua.py",
    "hyperbrowser/client/managers/async_manager/agents/cua.py",
)


def test_agent_managers_use_shared_start_payload_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_agent_start_payload(" in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
