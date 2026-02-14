import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


_ISINSTANCE_PLAIN_TYPE_PATTERN = re.compile(
    r"isinstance\s*\([^)]*,\s*(?:str|int)\s*\)"
)


def test_sdk_modules_avoid_isinstance_str_and_int_guards():
    violations: list[str] = []
    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        for line_number, line_text in enumerate(module_text.splitlines(), start=1):
            if _ISINSTANCE_PLAIN_TYPE_PATTERN.search(line_text):
                violations.append(f"{module_path}:{line_number}")

    assert violations == []
