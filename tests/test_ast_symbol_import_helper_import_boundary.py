from pathlib import Path

import pytest

from tests.ast_import_utils import imports_symbol_from_module
from tests.test_ast_symbol_import_helper_usage import AST_SYMBOL_IMPORT_GUARD_MODULES

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = (
    "tests/test_ast_import_utils.py",
    "tests/test_ast_symbol_import_helper_import_boundary.py",
    "tests/test_ast_symbol_import_helper_usage.py",
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

    expected_modules = sorted([*AST_SYMBOL_IMPORT_GUARD_MODULES, *EXPECTED_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
