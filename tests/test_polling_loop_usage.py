from pathlib import Path

import pytest

from tests.guardrail_ast_utils import collect_while_true_lines, read_module_ast

pytestmark = pytest.mark.architecture


ALLOWED_WHILE_TRUE_MODULES = {
    "hyperbrowser/client/polling.py",
}


def test_while_true_loops_are_centralized_to_polling_module():
    violations: list[str] = []
    polling_while_true_lines: list[int] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_ast = read_module_ast(module_path)
        while_true_lines = collect_while_true_lines(module_ast)
        if not while_true_lines:
            continue
        path_text = module_path.as_posix()
        if path_text in ALLOWED_WHILE_TRUE_MODULES:
            polling_while_true_lines.extend(while_true_lines)
            continue
        for line in while_true_lines:
            violations.append(f"{path_text}:{line}")

    assert violations == []
    assert polling_while_true_lines != []
