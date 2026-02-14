from pathlib import Path

import pytest

from tests.guardrail_ast_utils import collect_attribute_call_lines, read_module_ast

pytestmark = pytest.mark.architecture

MANAGERS_DIR = (
    Path(__file__).resolve().parents[1] / "hyperbrowser" / "client" / "managers"
)


def _manager_python_files() -> list[Path]:
    return sorted(
        path
        for path in MANAGERS_DIR.rglob("*.py")
        if path.name not in {"serialization_utils.py", "__init__.py"}
    )


def test_manager_modules_use_shared_serialization_helper_only():
    offending_calls: list[str] = []

    for path in _manager_python_files():
        module = read_module_ast(path)
        for line in collect_attribute_call_lines(module, "model_dump"):
            offending_calls.append(f"{path.relative_to(MANAGERS_DIR)}:{line}")

    assert offending_calls == []
