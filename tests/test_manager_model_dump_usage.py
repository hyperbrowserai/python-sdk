import ast
from pathlib import Path


MANAGERS_DIR = Path(__file__).resolve().parents[1] / "hyperbrowser" / "client" / "managers"


def _manager_python_files() -> list[Path]:
    return sorted(
        path
        for path in MANAGERS_DIR.rglob("*.py")
        if path.name not in {"serialization_utils.py", "__init__.py"}
    )


def test_manager_modules_use_shared_serialization_helper_only():
    offending_calls: list[str] = []

    for path in _manager_python_files():
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "model_dump":
                continue
            offending_calls.append(f"{path.relative_to(MANAGERS_DIR)}:{node.lineno}")

    assert offending_calls == []
