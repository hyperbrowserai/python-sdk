import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_MAPPING_UTILS_IMPORTERS = (
    "hyperbrowser/client/managers/list_parsing_utils.py",
    "hyperbrowser/client/managers/response_utils.py",
    "hyperbrowser/tools/__init__.py",
    "hyperbrowser/transport/base.py",
    "tests/test_mapping_utils.py",
)


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

    assert discovered_modules == list(EXPECTED_MAPPING_UTILS_IMPORTERS)
