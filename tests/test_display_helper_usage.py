import ast
from pathlib import Path


HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_NORMALIZE_DISPLAY_CALL_FILES = {
    Path("display_utils.py"),
    Path("client/managers/response_utils.py"),
    Path("transport/base.py"),
}


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def _collect_normalize_display_calls(module: ast.AST) -> list[int]:
    matches: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "normalize_display_text":
            continue
        matches.append(node.lineno)
    return matches


def _collect_format_key_calls(module: ast.AST) -> list[int]:
    matches: list[int] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "format_string_key_for_error":
            continue
        matches.append(node.lineno)
    return matches


def test_normalize_display_text_usage_is_centralized():
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(relative_path))
        normalize_calls = _collect_normalize_display_calls(module)
        if not normalize_calls:
            continue
        if relative_path in ALLOWED_NORMALIZE_DISPLAY_CALL_FILES:
            continue
        for line in normalize_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []


def test_key_formatting_helper_is_used_outside_display_module():
    helper_usage_files: set[Path] = set()

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        if relative_path == Path("display_utils.py"):
            continue
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(relative_path))
        if _collect_format_key_calls(module):
            helper_usage_files.add(relative_path)

    assert helper_usage_files != set()
