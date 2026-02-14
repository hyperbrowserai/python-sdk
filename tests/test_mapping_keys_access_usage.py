from pathlib import Path

import pytest

from tests.guardrail_ast_utils import collect_list_keys_call_lines, read_module_ast

pytestmark = pytest.mark.architecture

HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_KEYS_LIST_FILES = {
    Path("mapping_utils.py"),
    Path("client/managers/extension_utils.py"),
}


def _python_files() -> list[Path]:
    return sorted(HYPERBROWSER_ROOT.rglob("*.py"))


def test_mapping_key_iteration_is_centralized():
    violations: list[str] = []

    for path in _python_files():
        relative_path = path.relative_to(HYPERBROWSER_ROOT)
        module = read_module_ast(path)
        list_keys_calls = collect_list_keys_call_lines(module)
        if not list_keys_calls:
            continue
        if relative_path in ALLOWED_KEYS_LIST_FILES:
            continue
        for line in list_keys_calls:
            violations.append(f"{relative_path}:{line}")

    assert violations == []
