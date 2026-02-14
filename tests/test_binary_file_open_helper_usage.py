from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXTENSION_MODULES = (
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "hyperbrowser/client/managers/async_manager/extension.py",
)

SESSION_MODULES = (
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
)


def test_extension_managers_use_shared_binary_file_open_helper():
    for module_path in EXTENSION_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "open_binary_file(" in module_text
        assert 'with open(file_path, "rb")' not in module_text


def test_session_managers_use_upload_file_context_helper():
    for module_path in SESSION_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "open_upload_files_from_input(" in module_text
        assert "open_binary_file(" not in module_text
        assert 'with open(file_path, "rb")' not in module_text
