from pathlib import Path

import pytest

from tests.ast_import_utils import imports_symbol_from_module

pytestmark = pytest.mark.architecture


EXPECTED_SECONDARY_AST_IMPORT_HELPER_IMPORTERS = (
    "tests/test_ast_import_helper_import_boundary.py",
    "tests/test_ast_import_helper_usage.py",
    "tests/test_ast_import_utils.py",
)


def test_secondary_ast_import_helper_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="imports_imports_collect_function_sources",
        ):
            continue
        discovered_modules.append(module_path.as_posix())

    assert discovered_modules == list(EXPECTED_SECONDARY_AST_IMPORT_HELPER_IMPORTERS)
