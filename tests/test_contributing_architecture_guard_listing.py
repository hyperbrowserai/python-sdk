from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_contributing_lists_all_architecture_guard_modules():
    contributing_text = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    architecture_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "pytestmark = pytest.mark.architecture" not in module_text:
            continue
        architecture_modules.append(module_path.as_posix())

    assert architecture_modules != []
    for module_path in architecture_modules:
        assert module_path in contributing_text
