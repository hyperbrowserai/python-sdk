from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SYNC_MODULES = (
    "hyperbrowser/client/managers/sync_manager/extract.py",
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/sync_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/cua.py",
)

ASYNC_MODULES = (
    "hyperbrowser/client/managers/async_manager/extract.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/async_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/async_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/cua.py",
)


def test_sync_managers_use_wait_for_job_result_with_defaults():
    for module_path in SYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "wait_for_job_result_with_defaults(" in module_text
        assert "wait_for_job_result(" not in module_text
        assert "fetch_max_attempts=POLLING_ATTEMPTS" not in module_text
        assert "fetch_retry_delay_seconds=0.5" not in module_text


def test_async_managers_use_wait_for_job_result_with_defaults_async():
    for module_path in ASYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "wait_for_job_result_with_defaults_async(" in module_text
        assert "wait_for_job_result_async(" not in module_text
        assert "fetch_max_attempts=POLLING_ATTEMPTS" not in module_text
        assert "fetch_retry_delay_seconds=0.5" not in module_text
