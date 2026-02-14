import ast
from pathlib import Path


TOOLS_MODULE = Path("hyperbrowser/tools/__init__.py")


def _collect_keys_calls(module: ast.AST) -> list[int]:
    keys_calls: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "keys":
            keys_calls.append(node.lineno)
    return keys_calls


def _collect_helper_calls(module: ast.AST, helper_name: str) -> list[int]:
    helper_calls: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id == helper_name:
            helper_calls.append(node.lineno)
    return helper_calls


def test_tools_module_uses_shared_mapping_read_helpers():
    source = TOOLS_MODULE.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(TOOLS_MODULE))

    keys_calls = _collect_keys_calls(module)
    read_key_calls = _collect_helper_calls(module, "read_string_mapping_keys")
    copy_value_calls = _collect_helper_calls(
        module, "copy_mapping_values_by_string_keys"
    )

    assert keys_calls == []
    assert read_key_calls != []
    assert copy_value_calls != []
