import ast
from pathlib import Path

import pytest

from tests.test_safe_key_display_helper_usage import ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES

pytestmark = pytest.mark.architecture


EXPECTED_SAFE_KEY_DISPLAY_EXTRA_IMPORTERS = ("tests/test_mapping_utils.py",)


def _imports_safe_key_display_helper(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "hyperbrowser.mapping_utils":
            continue
        if any(alias.name == "safe_key_display_for_error" for alias in node.names):
            return True
    return False


def test_safe_key_display_helper_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_safe_key_display_helper(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_safe_key_display_helper(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_runtime_modules = sorted(
        f"hyperbrowser/{path.as_posix()}"
        for path in ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES
        if path != Path("mapping_utils.py")
    )
    expected_modules = sorted(
        [*expected_runtime_modules, *EXPECTED_SAFE_KEY_DISPLAY_EXTRA_IMPORTERS]
    )
    assert discovered_modules == expected_modules
