import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/session_upload_utils.py"


def test_session_upload_helper_uses_shared_operation_metadata_prefixes():
    module_text = Path(MODULE_PATH).read_text(encoding="utf-8")

    assert "session_operation_metadata import" in module_text
    assert "SESSION_OPERATION_METADATA.upload_missing_file_message_prefix" in module_text
    assert "SESSION_OPERATION_METADATA.upload_not_file_message_prefix" in module_text
    assert "SESSION_OPERATION_METADATA.upload_open_file_error_prefix" in module_text
    assert "SESSION_DEFAULT_UPLOAD_MISSING_FILE_MESSAGE_PREFIX" in module_text
    assert "SESSION_DEFAULT_UPLOAD_NOT_FILE_MESSAGE_PREFIX" in module_text
    assert "SESSION_DEFAULT_UPLOAD_OPEN_FILE_ERROR_PREFIX" in module_text
    assert (
        re.search(
            r'(?<!default_)prefix="Upload file not found at path"',
            module_text,
        )
        is None
    )
    assert (
        re.search(
            r'(?<!default_)prefix="Upload file path must point to a file"',
            module_text,
        )
        is None
    )
    assert (
        re.search(
            r'(?<!default_)prefix="Failed to open upload file at path"',
            module_text,
        )
        is None
    )
