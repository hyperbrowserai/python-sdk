from pathlib import Path

import pytest

from tests.test_list_parsing_helper_usage import (
    ALLOWED_PARSE_MAPPING_LIST_CALL_FILES,
    ALLOWED_READ_PLAIN_LIST_CALL_FILES,
)

pytestmark = pytest.mark.architecture


EXPECTED_LIST_PARSING_EXTRA_IMPORTERS = (
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

    expected_runtime_modules = sorted(
        f"hyperbrowser/{path.as_posix()}"
        for path in {
            *ALLOWED_PARSE_MAPPING_LIST_CALL_FILES,
            *ALLOWED_READ_PLAIN_LIST_CALL_FILES,
        }
        if path != Path("client/managers/list_parsing_utils.py")
    )
    expected_modules = sorted(
        [*expected_runtime_modules, *EXPECTED_LIST_PARSING_EXTRA_IMPORTERS]
    )
    assert discovered_modules == expected_modules
