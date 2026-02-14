from pathlib import Path

import pytest

from tests.ast_import_utils import imports_imports_collect_function_sources

pytestmark = pytest.mark.architecture


AST_IMPORT_GUARD_MODULES = (
    "tests/test_ast_function_source_helper_usage.py",
    "tests/test_ast_function_source_import_boundary.py",
)


def test_ast_import_guard_modules_reuse_shared_import_helper():
    violating_modules: list[str] = []
    for module_path in AST_IMPORT_GUARD_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if not imports_imports_collect_function_sources(module_text):
            violating_modules.append(module_path)
            continue
        if "imports_collect_function_sources(" not in module_text:
            violating_modules.append(module_path)
            continue
        if "def _imports_collect_function_sources" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []


def test_ast_import_guard_inventory_stays_in_sync_with_helper_imports():
    excluded_modules = {
        "tests/test_ast_import_helper_usage.py",
        "tests/test_ast_import_utils.py",
    }
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        normalized_path = module_path.as_posix()
        if normalized_path in excluded_modules:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_imports_collect_function_sources(module_text):
            continue
        discovered_modules.append(normalized_path)

    assert sorted(AST_IMPORT_GUARD_MODULES) == discovered_modules
