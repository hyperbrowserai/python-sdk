from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "hyperbrowser/client/managers/async_manager/extension.py",
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
)


def test_managers_use_shared_binary_file_open_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "open_binary_file(" in module_text
        assert 'with open(file_path, "rb")' not in module_text
