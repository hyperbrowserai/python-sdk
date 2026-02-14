import ast
from pathlib import Path


HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_KEYS_LIST_FILES = {
    Path("mapping_utils.py"),
    Path("client/managers/extension_utils.py"),
}


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def _collect_list_keys_calls(module: ast.AST) -> list[int]:
    matches: list[int] = []
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
        matches.append(node.lineno)
    return matches


def test_mapping_key_iteration_is_centralized():
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(relative_path))
        list_keys_calls = _collect_list_keys_calls(module)
        if not list_keys_calls:
            continue
        if relative_path in ALLOWED_KEYS_LIST_FILES:
            continue
        for line in list_keys_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []
