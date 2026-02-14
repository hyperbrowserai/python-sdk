from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGERS_DIR = Path("hyperbrowser/client/managers")


def test_started_job_context_primitives_are_centralized():
    violating_modules: list[str] = []
    for module_path in sorted(MANAGERS_DIR.rglob("*.py")):
        if module_path.name in {"__init__.py", "start_job_utils.py"}:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if "ensure_started_job_id(" in module_text or "build_operation_name(" in module_text:
            violating_modules.append(module_path.as_posix())

    assert violating_modules == []
