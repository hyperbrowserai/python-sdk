from pathlib import Path
import ast

import pytest

from tests.guardrail_ast_utils import collect_name_call_lines, read_module_ast

pytestmark = pytest.mark.architecture

HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES = {
    Path("mapping_utils.py"),
    Path("client/managers/extension_utils.py"),
    Path("client/managers/list_parsing_utils.py"),
}


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def test_safe_key_display_usage_is_centralized():
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        module = read_module_ast(path)
        helper_calls = collect_name_call_lines(module, "safe_key_display_for_error")
        if not helper_calls:
            continue
        if relative_path in ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES:
            continue
        for line in helper_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []


def test_safe_key_display_calls_use_explicit_key_display_keyword():
    missing_keyword_calls: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        if relative_path not in ALLOWED_SAFE_KEY_DISPLAY_CALL_FILES:
            continue
        module = read_module_ast(path)
        for node in ast.walk(module):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "safe_key_display_for_error":
                continue
            if any(keyword.arg == "key_display" for keyword in node.keywords):
                continue
            missing_keyword_calls.append(f"{relative_path}:{node.lineno}")

    assert missing_keyword_calls == []
