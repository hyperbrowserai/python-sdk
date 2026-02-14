import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_FILE_PATH_ERROR_MESSAGE_IMPORTERS = (
    "hyperbrowser/client/managers/extension_create_utils.py",
    "hyperbrowser/client/managers/session_upload_utils.py",
    "tests/test_file_utils.py",
)


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

    assert discovered_modules == list(EXPECTED_FILE_PATH_ERROR_MESSAGE_IMPORTERS)
