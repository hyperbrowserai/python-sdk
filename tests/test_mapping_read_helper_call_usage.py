from pathlib import Path

import pytest

from tests.guardrail_ast_utils import collect_name_call_lines, read_module_ast
from tests.test_mapping_reader_usage import MAPPING_READER_TARGET_FILES

pytestmark = pytest.mark.architecture

HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
EXPECTED_READ_HELPER_CALL_FILES = {
    path.relative_to("hyperbrowser") for path in MAPPING_READER_TARGET_FILES
}


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def test_read_string_key_mapping_usage_is_centralized():
    files_with_calls: set[Path] = set()
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        module = read_module_ast(path)
        helper_calls = collect_name_call_lines(module, "read_string_key_mapping")
        if not helper_calls:
            continue
        files_with_calls.add(relative_path)
        if relative_path in EXPECTED_READ_HELPER_CALL_FILES:
            continue
        for line in helper_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []
    assert files_with_calls == EXPECTED_READ_HELPER_CALL_FILES
