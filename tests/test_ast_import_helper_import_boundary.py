import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_AST_IMPORT_HELPER_IMPORTERS = (
    "tests/test_ast_function_source_helper_usage.py",
    "tests/test_ast_function_source_import_boundary.py",
)


def _imports_ast_import_helper(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "tests.ast_import_utils":
            continue
        if any(alias.name == "imports_collect_function_sources" for alias in node.names):
            return True
    return False


def test_ast_import_helper_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not _imports_ast_import_helper(module_text):
            continue
        discovered_modules.append(module_path.as_posix())

    assert discovered_modules == list(EXPECTED_AST_IMPORT_HELPER_IMPORTERS)
