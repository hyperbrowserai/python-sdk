import ast
from pathlib import Path

import pytest

from tests.test_tool_mapping_reader_usage import TOOLS_MODULE

pytestmark = pytest.mark.architecture


EXPECTED_READ_KEYS_HELPER_EXTRA_IMPORTERS = ("tests/test_mapping_utils.py",)


def _imports_read_string_mapping_keys(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "hyperbrowser.mapping_utils":
            continue
        if any(alias.name == "read_string_mapping_keys" for alias in node.names):
            return True
    return False


def test_read_string_mapping_keys_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_read_string_mapping_keys(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_read_string_mapping_keys(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_modules = sorted(
        [TOOLS_MODULE.as_posix(), *EXPECTED_READ_KEYS_HELPER_EXTRA_IMPORTERS]
    )
    assert discovered_modules == expected_modules
