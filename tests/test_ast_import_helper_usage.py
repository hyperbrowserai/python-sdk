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
        if "ast_import_utils import imports_collect_function_sources" not in module_text:
            violating_modules.append(module_path)
            continue
        if not imports_imports_collect_function_sources(module_text):
            violating_modules.append(module_path)
            continue
        if "imports_collect_function_sources(" not in module_text:
            violating_modules.append(module_path)
            continue
        if "def _imports_collect_function_sources" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []
