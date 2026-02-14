from pathlib import Path

import pytest

from tests.ast_import_utils import calls_symbol, imports_symbol_from_module

pytestmark = pytest.mark.architecture


AST_CALL_SYMBOL_GUARD_MODULES = (
    "tests/test_ast_function_source_helper_usage.py",
    "tests/test_ast_import_helper_usage.py",
    "tests/test_ast_symbol_import_helper_usage.py",
)


def test_ast_call_symbol_guard_modules_reuse_shared_helper():
    violating_modules: list[str] = []
    for module_path in AST_CALL_SYMBOL_GUARD_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if not imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="calls_symbol",
        ):
            violating_modules.append(module_path)
            continue
        if not calls_symbol(module_text, "calls_symbol"):
            violating_modules.append(module_path)
            continue
        if "def _calls_symbol" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []


def test_ast_call_symbol_guard_inventory_stays_in_sync():
    excluded_modules = {
        "tests/test_ast_call_symbol_helper_import_boundary.py",
        "tests/test_ast_call_symbol_helper_usage.py",
        "tests/test_ast_import_utils.py",
    }
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        normalized_path = module_path.as_posix()
        if normalized_path in excluded_modules:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="calls_symbol",
        ):
            continue
        discovered_modules.append(normalized_path)

    assert sorted(AST_CALL_SYMBOL_GUARD_MODULES) == discovered_modules
