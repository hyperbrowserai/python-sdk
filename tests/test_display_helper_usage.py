from pathlib import Path
import ast

import pytest

from tests.guardrail_ast_utils import collect_name_call_lines, read_module_ast

pytestmark = pytest.mark.architecture

HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_NORMALIZE_DISPLAY_CALL_FILES = {
    Path("display_utils.py"),
    Path("client/managers/response_utils.py"),
    Path("transport/base.py"),
}
ALLOWED_KEY_FORMAT_CALL_FILES = {
    Path("client/managers/extension_utils.py"),
    Path("client/managers/response_utils.py"),
    Path("client/managers/session_utils.py"),
    Path("tools/__init__.py"),
    Path("transport/base.py"),
}


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def test_normalize_display_text_usage_is_centralized():
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        module = read_module_ast(path)
        normalize_calls = collect_name_call_lines(module, "normalize_display_text")
        if not normalize_calls:
            continue
        if relative_path in ALLOWED_NORMALIZE_DISPLAY_CALL_FILES:
            continue
        for line in normalize_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []


def test_key_formatting_helper_usage_is_centralized():
    helper_usage_files: set[Path] = set()

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        if relative_path == Path("display_utils.py"):
            continue
        module = read_module_ast(path)
        if collect_name_call_lines(module, "format_string_key_for_error"):
            helper_usage_files.add(relative_path)

    assert helper_usage_files == ALLOWED_KEY_FORMAT_CALL_FILES


def test_key_formatting_helper_calls_use_explicit_max_length_keyword():
    missing_max_length_keyword_calls: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        if relative_path not in ALLOWED_KEY_FORMAT_CALL_FILES:
            continue
        module = read_module_ast(path)
        for node in ast.walk(module):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "format_string_key_for_error":
                continue
            if any(keyword.arg == "max_length" for keyword in node.keywords):
                continue
            missing_max_length_keyword_calls.append(f"{relative_path}:{node.lineno}")

    assert missing_max_length_keyword_calls == []
