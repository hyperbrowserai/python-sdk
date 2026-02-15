import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

LIST_PARSING_MODULE = Path("hyperbrowser/client/managers/list_parsing_utils.py")


def _imports_safe_key_display_for_error(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "hyperbrowser.mapping_utils":
            continue
        if any(alias.name == "safe_key_display_for_error" for alias in node.names):
            return True
    return False


def test_list_parsing_safe_key_display_helper_is_imported_from_mapping_utils():
    module_text = LIST_PARSING_MODULE.read_text(encoding="utf-8")
    assert _imports_safe_key_display_for_error(module_text)
