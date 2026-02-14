from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/job_fetch_utils.py",
    "hyperbrowser/client/managers/job_wait_utils.py",
)


def test_polling_default_helpers_use_shared_constants_module():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "from .polling_defaults import (" in module_text
        assert "DEFAULT_POLLING_RETRY_ATTEMPTS" in module_text
        assert "DEFAULT_POLLING_RETRY_DELAY_SECONDS" in module_text
        assert "POLLING_ATTEMPTS" not in module_text
        assert "retry_delay_seconds=0.5" not in module_text
