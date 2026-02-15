import ast
from pathlib import Path

import pytest

from tests.test_safe_key_display_helper_usage import ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES
from tests.test_mapping_reader_usage import MAPPING_READER_TARGET_FILES
from tests.test_tool_mapping_reader_usage import TOOLS_MODULE

pytestmark = pytest.mark.architecture


EXPECTED_MAPPING_EXTRA_IMPORTERS = ("tests/test_mapping_utils.py",)


def _imports_mapping_utils(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "hyperbrowser.mapping_utils":
            continue
        return True
    return False


def test_mapping_utils_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_mapping_utils(module_text):
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if _imports_mapping_utils(module_text):
            discovered_modules.append(module_path.as_posix())

    expected_runtime_modules = sorted(
        {
            *(path.as_posix() for path in MAPPING_READER_TARGET_FILES),
            TOOLS_MODULE.as_posix(),
            *(
                f"hyperbrowser/{path.as_posix()}"
                for path in ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES
                if path != Path("mapping_utils.py")
            ),
        }
    )
    expected_modules = sorted([*expected_runtime_modules, *EXPECTED_MAPPING_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
