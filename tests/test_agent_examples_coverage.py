from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_AGENT_EXAMPLES = (
    "async_browser_use_task.py",
    "async_claude_computer_use_task.py",
    "async_cua_task.py",
    "async_gemini_computer_use_task.py",
    "async_hyper_agent_task.py",
    "sync_browser_use_task.py",
    "sync_claude_computer_use_task.py",
    "sync_cua_task.py",
    "sync_gemini_computer_use_task.py",
    "sync_hyper_agent_task.py",
)


def test_agent_examples_cover_all_agent_task_managers():
    example_names = {path.name for path in Path("examples").glob("*.py")}
    assert set(EXPECTED_AGENT_EXAMPLES).issubset(example_names)
