from pathlib import Path

import pytest

from tests.ast_import_utils import (
    imports_imports_imports_imports_collect_function_sources,
)
from tests.test_ast_tertiary_import_helper_usage import (
    AST_TERTIARY_IMPORT_GUARD_MODULES,
)

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = ("tests/test_ast_import_utils.py",)


def test_tertiary_ast_import_helper_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_imports_imports_imports_collect_function_sources(module_text):
            continue
        discovered_modules.append(module_path.as_posix())

    expected_modules = sorted([*AST_TERTIARY_IMPORT_GUARD_MODULES, *EXPECTED_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
