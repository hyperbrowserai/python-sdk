from pathlib import Path

import pytest

from tests.guardrail_ast_utils import collect_name_call_lines, read_module_ast

pytestmark = pytest.mark.architecture

HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
LIST_PARSING_HELPER_RUNTIME_MODULES = {
    Path("client/managers/extension_utils.py"),
    Path("client/managers/list_parsing_utils.py"),
    Path("client/managers/session_utils.py"),
}
LIST_PARSING_HELPER_CALLER_MODULES = {
    path
    for path in LIST_PARSING_HELPER_RUNTIME_MODULES
    if path != Path("client/managers/list_parsing_utils.py")
}
ALLOWED_PARSE_MAPPING_LIST_CALL_FILES = LIST_PARSING_HELPER_CALLER_MODULES
ALLOWED_READ_PLAIN_LIST_CALL_FILES = LIST_PARSING_HELPER_CALLER_MODULES


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def test_parse_mapping_list_items_usage_is_centralized():
    files_with_calls: set[Path] = set()
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        module = read_module_ast(path)
        helper_calls = collect_name_call_lines(module, "parse_mapping_list_items")
        if not helper_calls:
            continue
        files_with_calls.add(relative_path)
        if relative_path in ALLOWED_PARSE_MAPPING_LIST_CALL_FILES:
            continue
        for line in helper_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []
    assert files_with_calls == ALLOWED_PARSE_MAPPING_LIST_CALL_FILES


def test_read_plain_list_items_usage_is_centralized():
    files_with_calls: set[Path] = set()
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        module = read_module_ast(path)
        helper_calls = collect_name_call_lines(module, "read_plain_list_items")
        if not helper_calls:
            continue
        files_with_calls.add(relative_path)
        if relative_path in ALLOWED_READ_PLAIN_LIST_CALL_FILES:
            continue
        for line in helper_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []
    assert files_with_calls == ALLOWED_READ_PLAIN_LIST_CALL_FILES
