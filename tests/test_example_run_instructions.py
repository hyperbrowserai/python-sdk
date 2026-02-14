from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_examples_include_python3_run_instructions():
    example_files = sorted(Path("examples").glob("*.py"))
    assert example_files != []

    for example_path in example_files:
        source = example_path.read_text(encoding="utf-8")
        assert "Run:" in source
        assert f"python3 examples/{example_path.name}" in source
