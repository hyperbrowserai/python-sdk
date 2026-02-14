import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


CORE_MODULES = (
    "hyperbrowser/config.py",
    "hyperbrowser/header_utils.py",
    "hyperbrowser/client/base.py",
    "hyperbrowser/client/polling.py",
)

_PLAIN_TYPE_CHECK_PATTERN = re.compile(
    r"type\s*\([^)]*\)\s+is(?:\s+not)?\s+(?:str|int)"
)


def test_core_modules_use_shared_plain_type_helpers():
    violations: list[str] = []
    for module_path in CORE_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        for line_number, line_text in enumerate(module_text.splitlines(), start=1):
            if _PLAIN_TYPE_CHECK_PATTERN.search(line_text):
                violations.append(f"{module_path}:{line_number}")

    assert violations == []
