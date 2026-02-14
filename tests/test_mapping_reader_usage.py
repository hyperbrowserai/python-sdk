import ast
from pathlib import Path


_TARGET_FILES = (
    Path("hyperbrowser/client/managers/response_utils.py"),
    Path("hyperbrowser/transport/base.py"),
    Path("hyperbrowser/client/managers/list_parsing_utils.py"),
)


def _collect_list_keys_calls(module: ast.AST) -> list[int]:
    key_calls: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "list":
            continue
        if len(node.args) != 1:
            continue
        argument = node.args[0]
        if not isinstance(argument, ast.Call):
            continue
        if not isinstance(argument.func, ast.Attribute):
            continue
        if argument.func.attr != "keys":
            continue
        key_calls.append(node.lineno)
    return key_calls


def _collect_mapping_reader_calls(module: ast.AST) -> list[int]:
    reader_calls: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "read_string_key_mapping":
            reader_calls.append(node.lineno)
    return reader_calls


def test_core_mapping_parsers_use_shared_mapping_reader():
    violations: list[str] = []
    missing_reader_calls: list[str] = []

    for relative_path in _TARGET_FILES:
        source = relative_path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(relative_path))
        list_keys_calls = _collect_list_keys_calls(module)
        if list_keys_calls:
            for line in list_keys_calls:
                violations.append(f"{relative_path}:{line}")
        reader_calls = _collect_mapping_reader_calls(module)
        if not reader_calls:
            missing_reader_calls.append(str(relative_path))

    assert violations == []
    assert missing_reader_calls == []
