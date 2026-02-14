import ast
from pathlib import Path

import pytest

from tests.test_display_helper_usage import ALLOWED_KEY_FORMAT_CALL_FILES

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = ("tests/test_display_utils.py",)


def _imports_format_string_key_for_error(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if any(alias.name == "format_string_key_for_error" for alias in node.names):
            return True
    return False


def test_format_string_key_for_error_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_format_string_key_for_error(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_format_string_key_for_error(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_modules = sorted(
        [
            *(f"hyperbrowser/{path.as_posix()}" for path in ALLOWED_KEY_FORMAT_CALL_FILES),
            *EXPECTED_EXTRA_IMPORTERS,
        ]
    )
    assert discovered_modules == expected_modules
