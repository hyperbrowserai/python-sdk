from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGERS_DIR = Path("hyperbrowser/client/managers")


def test_poll_until_terminal_status_primitives_are_centralized():
    violating_modules: list[str] = []
    for module_path in sorted(MANAGERS_DIR.rglob("*.py")):
        if module_path.name in {"__init__.py", "job_poll_utils.py"}:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if (
            "from ..polling import poll_until_terminal_status" in module_text
            or "from ..polling import poll_until_terminal_status_async" in module_text
            or "from ...polling import poll_until_terminal_status" in module_text
            or "from ...polling import poll_until_terminal_status_async" in module_text
            or "from ....polling import poll_until_terminal_status" in module_text
            or "from ....polling import poll_until_terminal_status_async" in module_text
        ):
            violating_modules.append(module_path.as_posix())

    assert violating_modules == []
