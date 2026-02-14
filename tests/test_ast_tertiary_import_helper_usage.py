from pathlib import Path

import pytest

from tests.ast_import_utils import (
    calls_symbol,
    imports_imports_imports_imports_collect_function_sources,
)

pytestmark = pytest.mark.architecture


AST_TERTIARY_IMPORT_GUARD_MODULES = (
    "tests/test_ast_import_helper_secondary_import_boundary.py",
    "tests/test_ast_secondary_import_helper_usage.py",
)


def test_ast_tertiary_import_guard_modules_reuse_shared_helper():
    violating_modules: list[str] = []
    for module_path in AST_TERTIARY_IMPORT_GUARD_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if not imports_imports_imports_imports_collect_function_sources(module_text):
            violating_modules.append(module_path)
            continue
        if not calls_symbol(module_text, "imports_imports_imports_collect_function_sources"):
            violating_modules.append(module_path)
            continue
        if "def _imports_imports_imports_collect_function_sources" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []


def test_ast_tertiary_import_guard_inventory_stays_in_sync():
    excluded_modules = {
        "tests/test_ast_import_utils.py",
        "tests/test_ast_tertiary_import_helper_import_boundary.py",
        "tests/test_ast_tertiary_import_helper_usage.py",
    }
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        normalized_path = module_path.as_posix()
        if normalized_path in excluded_modules:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_imports_imports_imports_collect_function_sources(module_text):
            continue
        discovered_modules.append(normalized_path)

    assert sorted(AST_TERTIARY_IMPORT_GUARD_MODULES) == discovered_modules
