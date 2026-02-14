from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_pyproject_registers_architecture_pytest_marker():
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'markers = [' in pyproject_text
    assert "architecture: architecture/guardrail quality gate tests" in pyproject_text
