from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_EXPECTATIONS = (
    (
        "hyperbrowser/client/managers/extension_create_utils.py",
        {
            "EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX": (
                "default_prefix=EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX"
            ),
            "EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX": (
                "default_prefix=EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX"
            ),
        },
    ),
    (
        "hyperbrowser/client/managers/sync_manager/extension.py",
        {
            "EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX": (
                "default_prefix=EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX"
            ),
        },
    ),
    (
        "hyperbrowser/client/managers/async_manager/extension.py",
        {
            "EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX": (
                "default_prefix=EXTENSION_DEFAULT_OPEN_FILE_ERROR_PREFIX"
            ),
        },
    ),
    (
        "hyperbrowser/client/managers/session_upload_utils.py",
        {
            "SESSION_DEFAULT_UPLOAD_MISSING_FILE_MESSAGE_PREFIX": (
                "default_prefix=SESSION_DEFAULT_UPLOAD_MISSING_FILE_MESSAGE_PREFIX"
            ),
            "SESSION_DEFAULT_UPLOAD_NOT_FILE_MESSAGE_PREFIX": (
                "default_prefix=SESSION_DEFAULT_UPLOAD_NOT_FILE_MESSAGE_PREFIX"
            ),
            "SESSION_DEFAULT_UPLOAD_OPEN_FILE_ERROR_PREFIX": (
                "default_prefix=SESSION_DEFAULT_UPLOAD_OPEN_FILE_ERROR_PREFIX"
            ),
        },
    ),
)

FORBIDDEN_DEFAULT_PREFIX_LITERALS = (
    'default_prefix="Extension file not found at path"',
    'default_prefix="Extension file path must point to a file"',
    'default_prefix="Failed to open extension file at path"',
    'default_prefix="Upload file not found at path"',
    'default_prefix="Upload file path must point to a file"',
    'default_prefix="Failed to open upload file at path"',
)


def test_file_message_helpers_use_shared_default_prefix_constants():
    for module_path, expected_default_prefix_constants in MODULE_EXPECTATIONS:
        module_text = Path(module_path).read_text(encoding="utf-8")
        for constant_name, expected_default_assignment in (
            expected_default_prefix_constants.items()
        ):
            assert constant_name in module_text
            assert expected_default_assignment in module_text
        for forbidden_literal in FORBIDDEN_DEFAULT_PREFIX_LITERALS:
            assert forbidden_literal not in module_text
