from pathlib import Path

from tests.guardrail_ast_utils import collect_name_call_lines, read_module_ast

HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_NORMALIZE_DISPLAY_CALL_FILES = {
    Path("display_utils.py"),
    Path("client/managers/response_utils.py"),
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


def test_key_formatting_helper_is_used_outside_display_module():
    helper_usage_files: set[Path] = set()

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        if relative_path == Path("display_utils.py"):
            continue
        module = read_module_ast(path)
        if collect_name_call_lines(module, "format_string_key_for_error"):
            helper_usage_files.add(relative_path)

    assert helper_usage_files != set()
