from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/extract.py",
    "hyperbrowser/client/managers/async_manager/extract.py",
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
    "hyperbrowser/client/managers/sync_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/async_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/async_manager/agents/hyper_agent.py",
    "hyperbrowser/client/managers/sync_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/gemini_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/async_manager/agents/claude_computer_use.py",
    "hyperbrowser/client/managers/sync_manager/agents/cua.py",
    "hyperbrowser/client/managers/async_manager/agents/cua.py",
)


def test_managers_use_shared_started_job_context_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_started_job_context(" in module_text
        assert "ensure_started_job_id(" not in module_text
        assert "build_operation_name(" not in module_text
