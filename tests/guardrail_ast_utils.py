import ast
from pathlib import Path


def read_module_ast(path: Path) -> ast.AST:
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def collect_name_call_lines(module: ast.AST, name: str) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != name:
            continue
        lines.append(node.lineno)
    return lines


def collect_attribute_call_lines(module: ast.AST, attribute_name: str) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != attribute_name:
            continue
        lines.append(node.lineno)
    return lines


def collect_list_keys_call_lines(module: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "list":
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
        lines.append(node.lineno)
    return lines


def collect_while_true_lines(module: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.While):
            continue
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            lines.append(node.lineno)
    return lines
