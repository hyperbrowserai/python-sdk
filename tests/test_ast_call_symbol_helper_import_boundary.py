from pathlib import Path

import pytest

from tests.ast_import_utils import imports_symbol_from_module

pytestmark = pytest.mark.architecture


EXPECTED_CALLS_SYMBOL_IMPORTERS = (
    "tests/test_ast_function_source_helper_usage.py",
    "tests/test_ast_import_helper_usage.py",
    "tests/test_ast_import_utils.py",
)


def test_calls_symbol_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="calls_symbol",
        ):
            continue
        discovered_modules.append(module_path.as_posix())

    assert discovered_modules == list(EXPECTED_CALLS_SYMBOL_IMPORTERS)
