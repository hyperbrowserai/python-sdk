from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SYNC_MODULES = (
    "hyperbrowser/client/managers/sync_manager/scrape.py",
    "hyperbrowser/client/managers/sync_manager/crawl.py",
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
)

ASYNC_MODULES = (
    "hyperbrowser/client/managers/async_manager/scrape.py",
    "hyperbrowser/client/managers/async_manager/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_sync_managers_use_job_poll_helpers():
    for module_path in SYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert (
            "poll_job_until_terminal_status as poll_until_terminal_status"
            in module_text
        )
        assert "poll_until_terminal_status(" in module_text
        assert "from ..polling import" not in module_text
        assert "from ...polling import" not in module_text
        assert "from ....polling import" not in module_text


def test_async_managers_use_job_poll_helpers():
    for module_path in ASYNC_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert (
            "poll_job_until_terminal_status_async as poll_until_terminal_status_async"
            in module_text
        )
        assert "poll_until_terminal_status_async(" in module_text
        assert "from ..polling import" not in module_text
        assert "from ...polling import" not in module_text
        assert "from ....polling import" not in module_text
