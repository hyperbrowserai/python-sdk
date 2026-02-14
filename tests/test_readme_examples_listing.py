import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_readme_example_list_references_existing_example_files():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    listed_examples = re.findall(r"- `([^`]*examples/[^`]*)`", readme_text)

    assert listed_examples != []
    for example_path in listed_examples:
        assert Path(example_path).is_file()
