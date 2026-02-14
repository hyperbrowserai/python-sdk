import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_example_scripts_follow_sync_async_prefix_naming():
    example_files = sorted(Path("examples").glob("*.py"))
    assert example_files != []

    pattern = re.compile(r"^(sync|async)_[a-z0-9_]+\.py$")
    for example_path in example_files:
        assert pattern.fullmatch(example_path.name)
