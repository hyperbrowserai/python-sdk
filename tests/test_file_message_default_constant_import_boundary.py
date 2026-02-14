from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_EXTENSION_DEFAULT_CONSTANT_CONSUMERS = (
    "hyperbrowser/client/managers/async_manager/extension.py",
    "hyperbrowser/client/managers/extension_create_utils.py",
    "hyperbrowser/client/managers/extension_operation_metadata.py",
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "tests/test_extension_create_metadata_usage.py",
    "tests/test_extension_operation_metadata.py",
    "tests/test_extension_operation_metadata_usage.py",
    "tests/test_file_message_default_constant_import_boundary.py",
    "tests/test_file_message_default_constant_usage.py",
    "tests/test_file_open_error_helper_usage.py",
)

EXPECTED_SESSION_DEFAULT_CONSTANT_CONSUMERS = (
    "hyperbrowser/client/managers/session_operation_metadata.py",
    "hyperbrowser/client/managers/session_upload_utils.py",
    "tests/test_file_message_default_constant_import_boundary.py",
    "tests/test_file_message_default_constant_usage.py",
    "tests/test_file_open_error_helper_usage.py",
    "tests/test_session_operation_metadata.py",
    "tests/test_session_upload_metadata_usage.py",
)


def _discover_modules_with_text(fragment: str) -> list[str]:
    discovered_modules: list[str] = []
    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if fragment not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if fragment not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())
    return discovered_modules


def test_extension_default_message_constants_are_centralized():
    discovered_modules = _discover_modules_with_text("EXTENSION_DEFAULT_")
    assert discovered_modules == list(EXPECTED_EXTENSION_DEFAULT_CONSTANT_CONSUMERS)


def test_session_default_message_constants_are_centralized():
    discovered_modules = _discover_modules_with_text("SESSION_DEFAULT_UPLOAD_")
    assert discovered_modules == list(EXPECTED_SESSION_DEFAULT_CONSTANT_CONSUMERS)
