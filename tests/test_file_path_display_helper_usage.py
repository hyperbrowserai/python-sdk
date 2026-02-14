from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


FILE_PATH_DISPLAY_MODULES = (
    "hyperbrowser/client/managers/extension_create_utils.py",
    "hyperbrowser/client/managers/session_upload_utils.py",
)


def test_file_path_error_messages_use_shared_display_helper():
    for module_path in FILE_PATH_DISPLAY_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_file_path_error_message(" in module_text
        assert "format_file_path_for_error(" not in module_text
        assert 'missing_file_message=f"' not in module_text
        assert 'not_file_message=f"' not in module_text
        assert "ord(character) < 32" not in module_text
