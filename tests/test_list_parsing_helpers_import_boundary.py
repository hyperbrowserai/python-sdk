from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_LIST_PARSING_HELPER_IMPORTERS = (
    "hyperbrowser/client/managers/extension_utils.py",
    "hyperbrowser/client/managers/session_utils.py",
    "tests/test_list_parsing_helpers_import_boundary.py",
    "tests/test_list_parsing_utils.py",
)


def test_list_parsing_helper_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "list_parsing_utils import" not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "list_parsing_utils import" not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())

    assert discovered_modules == list(EXPECTED_LIST_PARSING_HELPER_IMPORTERS)
