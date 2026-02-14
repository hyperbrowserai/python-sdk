from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGERS_DIR = Path("hyperbrowser/client/managers")


def test_wait_for_job_result_primitives_are_centralized():
    violating_modules: list[str] = []
    for module_path in sorted(MANAGERS_DIR.rglob("*.py")):
        if module_path.name in {"__init__.py", "job_wait_utils.py"}:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if "wait_for_job_result(" in module_text or "wait_for_job_result_async(" in module_text:
            violating_modules.append(module_path.as_posix())

    assert violating_modules == []
