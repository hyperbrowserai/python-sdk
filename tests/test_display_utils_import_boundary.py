from pathlib import Path

import pytest

from tests.test_display_helper_usage import (
    ALLOWED_KEY_FORMAT_CALL_FILES,
    ALLOWED_NORMALIZE_DISPLAY_CALL_FILES,
)

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = (
    "tests/test_display_utils.py",
    "tests/test_display_utils_import_boundary.py",
    "tests/test_extension_key_display_import_boundary.py",
)


def test_display_utils_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "hyperbrowser.display_utils" not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "hyperbrowser.display_utils" not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())

    expected_runtime_modules = sorted(
        f"hyperbrowser/{path.as_posix()}"
        for path in {
            *ALLOWED_KEY_FORMAT_CALL_FILES,
            *ALLOWED_NORMALIZE_DISPLAY_CALL_FILES,
        }
        if path != Path("display_utils.py")
    )
    expected_modules = sorted([*expected_runtime_modules, *EXPECTED_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
