from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_examples_have_sync_async_parity_by_prefix():
    example_names = {path.stem for path in Path("examples").glob("*.py")}

    sync_examples = {name for name in example_names if name.startswith("sync_")}
    async_examples = {name for name in example_names if name.startswith("async_")}

    assert sync_examples != []
    assert async_examples != []

    for sync_name in sync_examples:
        expected_async = sync_name.replace("sync_", "async_", 1)
        assert expected_async in example_names

    for async_name in async_examples:
        expected_sync = async_name.replace("async_", "sync_", 1)
        assert expected_sync in example_names
