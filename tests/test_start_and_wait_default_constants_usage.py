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


def test_start_and_wait_managers_use_shared_default_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "DEFAULT_POLL_INTERVAL_SECONDS" in module_text
        assert "DEFAULT_MAX_WAIT_SECONDS" in module_text
        assert "DEFAULT_POLLING_RETRY_ATTEMPTS" in module_text
        assert "poll_interval_seconds: float = 2.0" not in module_text
        assert "max_wait_seconds: Optional[float] = 600.0" not in module_text
        assert "max_status_failures: int = POLLING_ATTEMPTS" not in module_text
