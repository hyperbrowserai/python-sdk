from pathlib import Path

import pytest

from tests.test_file_message_default_constant_usage import MODULE_EXPECTATIONS

pytestmark = pytest.mark.architecture


EXPECTED_EXTENSION_EXTRA_CONSUMERS = (
    "hyperbrowser/client/managers/extension_operation_metadata.py",
    "tests/test_extension_create_metadata_usage.py",
    "tests/test_extension_operation_metadata.py",
    "tests/test_extension_operation_metadata_usage.py",
    "tests/test_file_message_default_constant_import_boundary.py",
    "tests/test_file_message_default_constant_usage.py",
    "tests/test_file_open_error_helper_usage.py",
)

EXPECTED_SESSION_EXTRA_CONSUMERS = (
    "hyperbrowser/client/managers/session_operation_metadata.py",
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


def _runtime_consumers_for_prefix(prefix: str) -> list[str]:
    runtime_modules: list[str] = []
    for module_path, expected_default_prefix_constants in MODULE_EXPECTATIONS:
        if not any(
            constant_name.startswith(prefix)
            for constant_name in expected_default_prefix_constants
        ):
            continue
        runtime_modules.append(module_path)
    return runtime_modules


def test_extension_default_message_constants_are_centralized():
    discovered_modules = _discover_modules_with_text("EXTENSION_DEFAULT_")
    expected_modules = sorted(
        [*_runtime_consumers_for_prefix("EXTENSION_DEFAULT_"), *EXPECTED_EXTENSION_EXTRA_CONSUMERS]
    )
    assert discovered_modules == expected_modules


def test_session_default_message_constants_are_centralized():
    discovered_modules = _discover_modules_with_text("SESSION_DEFAULT_UPLOAD_")
    expected_modules = sorted(
        [*_runtime_consumers_for_prefix("SESSION_DEFAULT_UPLOAD_"), *EXPECTED_SESSION_EXTRA_CONSUMERS]
    )
    assert discovered_modules == expected_modules
