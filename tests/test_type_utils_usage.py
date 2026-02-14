from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_type_mro_checks_are_centralized_in_type_utils():
    violations: list[str] = []
    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        if module_path.as_posix() == "hyperbrowser/type_utils.py":
            continue
        module_text = module_path.read_text(encoding="utf-8")
        for line_number, line_text in enumerate(module_text.splitlines(), start=1):
            if "__mro__" in line_text:
                violations.append(f"{module_path}:{line_number}")

    assert violations == []
