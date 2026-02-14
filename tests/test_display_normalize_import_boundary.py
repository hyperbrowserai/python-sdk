import ast
from pathlib import Path

import pytest

from tests.test_display_helper_usage import ALLOWED_NORMALIZE_DISPLAY_CALL_FILES

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = ("tests/test_display_utils.py",)


def _imports_normalize_display_text(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if any(alias.name == "normalize_display_text" for alias in node.names):
            return True
    return False


def test_normalize_display_text_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_normalize_display_text(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_normalize_display_text(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_runtime_modules = sorted(
        f"hyperbrowser/{path.as_posix()}"
        for path in ALLOWED_NORMALIZE_DISPLAY_CALL_FILES
        if path != Path("display_utils.py")
    )
    expected_modules = sorted([*expected_runtime_modules, *EXPECTED_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
