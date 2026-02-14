import ast
from pathlib import Path

import pytest

from tests.test_ast_function_source_helper_usage import (
    AST_FUNCTION_SOURCE_GUARD_MODULES,
)

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTER_MODULES = ("tests/test_ast_function_source_utils.py",)

def _imports_collect_function_sources(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "tests.ast_function_source_utils":
            continue
        if any(alias.name == "collect_function_sources" for alias in node.names):
            return True
    return False


def test_ast_function_source_helper_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not _imports_collect_function_sources(module_text):
            continue
        discovered_modules.append(module_path.as_posix())

    expected_modules = sorted(
        [*AST_FUNCTION_SOURCE_GUARD_MODULES, *EXPECTED_EXTRA_IMPORTER_MODULES]
    )
    assert discovered_modules == expected_modules
