from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/async_manager/web/batch_fetch.py",
    "hyperbrowser/client/managers/sync_manager/web/crawl.py",
    "hyperbrowser/client/managers/async_manager/web/crawl.py",
)


def test_web_managers_use_shared_operation_metadata():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "web_operation_metadata import" in module_text
        assert "_OPERATION_METADATA = " in module_text
        assert "operation_name=self._OPERATION_METADATA." in module_text
        assert "start_error_message=self._OPERATION_METADATA." in module_text
        assert "operation_name_prefix=self._OPERATION_METADATA." in module_text
        assert 'operation_name="' not in module_text
        assert 'start_error_message="' not in module_text
        assert 'operation_name_prefix="' not in module_text
