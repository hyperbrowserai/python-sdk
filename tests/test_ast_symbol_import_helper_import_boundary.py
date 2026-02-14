from pathlib import Path

import pytest

from tests.ast_import_utils import imports_symbol_from_module

pytestmark = pytest.mark.architecture


EXPECTED_IMPORTS_SYMBOL_FROM_MODULE_IMPORTERS = (
    "tests/test_ast_call_symbol_helper_import_boundary.py",
    "tests/test_ast_import_helper_secondary_import_boundary.py",
    "tests/test_ast_import_helper_usage.py",
    "tests/test_ast_import_utils.py",
    "tests/test_ast_module_import_helper_import_boundary.py",
    "tests/test_ast_symbol_import_helper_import_boundary.py",
)


def test_imports_symbol_from_module_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="imports_symbol_from_module",
        ):
            continue
        discovered_modules.append(module_path.as_posix())

    assert discovered_modules == list(EXPECTED_IMPORTS_SYMBOL_FROM_MODULE_IMPORTERS)
