import ast
from pathlib import Path

import pytest

from tests.test_file_path_display_helper_usage import FILE_PATH_DISPLAY_MODULES

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = ("tests/test_file_utils.py",)


def _imports_build_file_path_error_message(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if any(alias.name == "build_file_path_error_message" for alias in node.names):
            return True
    return False


def test_build_file_path_error_message_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_build_file_path_error_message(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_build_file_path_error_message(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_modules = sorted([*FILE_PATH_DISPLAY_MODULES, *EXPECTED_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
