import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_example_scripts_have_valid_python_syntax():
    example_files = sorted(Path("examples").glob("*.py"))
    assert example_files != []

    for example_path in example_files:
        source = example_path.read_text(encoding="utf-8")
        ast.parse(source, filename=example_path.as_posix())
