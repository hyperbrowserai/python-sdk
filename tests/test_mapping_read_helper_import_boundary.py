import ast
from pathlib import Path

import pytest

from tests.test_mapping_utils_import_boundary import EXPECTED_MAPPING_EXTRA_IMPORTERS
from tests.test_mapping_reader_usage import MAPPING_READER_TARGET_FILES

pytestmark = pytest.mark.architecture


def _imports_read_string_key_mapping(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "hyperbrowser.mapping_utils":
            continue
        if any(alias.name == "read_string_key_mapping" for alias in node.names):
            return True
    return False


def test_read_string_key_mapping_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_read_string_key_mapping(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_read_string_key_mapping(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_runtime_modules = sorted(
        path.as_posix() for path in MAPPING_READER_TARGET_FILES
    )
    expected_modules = sorted(
        [*expected_runtime_modules, *EXPECTED_MAPPING_EXTRA_IMPORTERS]
    )
    assert discovered_modules == expected_modules
