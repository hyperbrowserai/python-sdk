from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "hyperbrowser/client/managers/async_manager/extension.py",
)


def test_extension_managers_use_shared_operation_metadata():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "extension_operation_metadata import" in module_text
        assert "_OPERATION_METADATA = " in module_text
        assert "operation_name=self._OPERATION_METADATA." in module_text
        assert "prefix=self._OPERATION_METADATA.open_file_error_prefix" in module_text
        assert 'operation_name="' not in module_text
        assert 'prefix="Failed to open extension file at path"' not in module_text
