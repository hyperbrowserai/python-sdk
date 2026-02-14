from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


OPEN_ERROR_HELPER_MODULES = (
    "hyperbrowser/client/managers/session_upload_utils.py",
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "hyperbrowser/client/managers/async_manager/extension.py",
)


def test_file_open_error_messages_use_shared_helper():
    for module_path in OPEN_ERROR_HELPER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_open_file_error_message(" in module_text
        assert "open_error_message=f\"" not in module_text
