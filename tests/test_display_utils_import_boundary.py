from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_DISPLAY_UTILS_IMPORTERS = (
    "hyperbrowser/client/managers/extension_utils.py",
    "hyperbrowser/client/managers/response_utils.py",
    "hyperbrowser/client/managers/session_utils.py",
    "hyperbrowser/tools/__init__.py",
    "hyperbrowser/transport/base.py",
    "tests/test_display_utils.py",
    "tests/test_display_utils_import_boundary.py",
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

    assert discovered_modules == list(EXPECTED_DISPLAY_UTILS_IMPORTERS)
