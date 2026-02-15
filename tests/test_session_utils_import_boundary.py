import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

SESSION_UTILS_MODULE = Path("hyperbrowser/client/managers/session_utils.py")


def _imports_symbol_from_module(
    module_text: str,
    *,
    module_name: str,
    symbol_name: str,
    module_level: int = 0,
) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != module_name:
            continue
        if node.level != module_level:
            continue
        if any(alias.name == symbol_name for alias in node.names):
            return True
    return False


def test_session_utils_imports_parse_response_model_from_response_utils():
    module_text = SESSION_UTILS_MODULE.read_text(encoding="utf-8")
    assert _imports_symbol_from_module(
        module_text,
        module_name="response_utils",
        symbol_name="parse_response_model",
        module_level=1,
    )


def test_session_utils_imports_list_parsing_helpers_from_list_parsing_utils():
    module_text = SESSION_UTILS_MODULE.read_text(encoding="utf-8")
    assert _imports_symbol_from_module(
        module_text,
        module_name="list_parsing_utils",
        symbol_name="read_plain_list_items",
        module_level=1,
    )
    assert _imports_symbol_from_module(
        module_text,
        module_name="list_parsing_utils",
        symbol_name="parse_mapping_list_items",
        module_level=1,
    )
