import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_readme_and_contributing_use_python3_commands():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    contributing_text = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "python -m" not in readme_text
    assert "python -m" not in contributing_text
    assert not re.search(r"^\s*pip install -e \. pytest ruff build\s*$", readme_text, re.MULTILINE)
    assert "python3 -m pip install -e . pytest ruff build" in readme_text


def test_example_run_blocks_use_python3():
    legacy_python_pattern = re.compile(r"^\s*python\s+examples/.*$", re.MULTILINE)

    for example_path in sorted(Path("examples").glob("*.py")):
        example_text = example_path.read_text(encoding="utf-8")
        assert not legacy_python_pattern.search(example_text)
