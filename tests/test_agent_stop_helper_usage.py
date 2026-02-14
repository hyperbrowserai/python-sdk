from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SYNC_MODULES = (
    "hyperbrowser/client/managers/sync_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/sync_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/cua.py",
)

ASYNC_MODULES = (
    "hyperbrowser/client/managers/async_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/async_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/async_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/cua.py",
)


def test_sync_agent_managers_use_shared_stop_helper():
    for module_path in SYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "stop_agent_task(" in module_text
        assert "/stop\")" not in module_text


def test_async_agent_managers_use_shared_stop_helper():
    for module_path in ASYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "stop_agent_task_async(" in module_text
        assert "/stop\")" not in module_text
