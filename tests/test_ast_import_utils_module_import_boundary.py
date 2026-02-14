from pathlib import Path

import pytest

from tests.ast_import_utils import imports_from_module
from tests.test_ast_call_symbol_helper_usage import AST_CALL_SYMBOL_GUARD_MODULES
from tests.test_ast_import_helper_usage import AST_IMPORT_GUARD_MODULES
from tests.test_ast_secondary_import_helper_usage import (
    AST_SECONDARY_IMPORT_GUARD_MODULES,
)

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = (
    "tests/test_ast_call_symbol_helper_import_boundary.py",
    "tests/test_ast_call_symbol_helper_usage.py",
    "tests/test_ast_import_helper_import_boundary.py",
    "tests/test_ast_import_helper_secondary_import_boundary.py",
    "tests/test_ast_module_import_helper_import_boundary.py",
    "tests/test_ast_module_import_helper_usage.py",
    "tests/test_ast_quaternary_import_helper_import_boundary.py",
    "tests/test_ast_quaternary_import_helper_usage.py",
    "tests/test_ast_secondary_import_helper_usage.py",
    "tests/test_ast_symbol_import_helper_import_boundary.py",
    "tests/test_ast_symbol_import_helper_usage.py",
    "tests/test_ast_tertiary_import_helper_import_boundary.py",
    "tests/test_ast_tertiary_import_helper_usage.py",
    "tests/test_ast_import_utils.py",
    "tests/test_ast_import_utils_module_import_boundary.py",
)


def test_ast_import_utils_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_from_module(module_text, module="tests.ast_import_utils"):
            continue
        discovered_modules.append(module_path.as_posix())

    expected_modules = sorted(
        {
            *AST_IMPORT_GUARD_MODULES,
            *AST_CALL_SYMBOL_GUARD_MODULES,
            *AST_SECONDARY_IMPORT_GUARD_MODULES,
            *EXPECTED_EXTRA_IMPORTERS,
        }
    )
    assert discovered_modules == expected_modules
