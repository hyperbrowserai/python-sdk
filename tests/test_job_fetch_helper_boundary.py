from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGERS_DIR = Path("hyperbrowser/client/managers")


def test_retry_and_paginated_fetch_primitives_are_centralized():
    violating_modules: list[str] = []
    for module_path in sorted(MANAGERS_DIR.rglob("*.py")):
        if module_path.name in {"__init__.py", "job_fetch_utils.py"}:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if (
            "retry_operation(" in module_text
            or "retry_operation_async(" in module_text
            or "collect_paginated_results(" in module_text
            or "collect_paginated_results_async(" in module_text
            or "build_fetch_operation_name(" in module_text
        ):
            violating_modules.append(module_path.as_posix())

    assert violating_modules == []
