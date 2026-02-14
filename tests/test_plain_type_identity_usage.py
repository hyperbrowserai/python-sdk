import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


_PLAIN_TYPE_IDENTITY_PATTERN = re.compile(
    r"type\s*\([^)]*\)\s+is(?:\s+not)?\s+(?:str|int)\b"
)


def test_sdk_modules_avoid_direct_str_int_type_identity_checks():
    violations: list[str] = []
    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        for line_number, line_text in enumerate(module_text.splitlines(), start=1):
            if _PLAIN_TYPE_IDENTITY_PATTERN.search(line_text):
                violations.append(f"{module_path}:{line_number}")

    assert violations == []
