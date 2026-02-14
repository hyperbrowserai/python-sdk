from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/extension_create_utils.py"


def test_extension_create_helper_uses_shared_operation_metadata_prefixes():
    module_text = Path(MODULE_PATH).read_text(encoding="utf-8")

    assert "extension_operation_metadata import" in module_text
    assert "EXTENSION_OPERATION_METADATA.missing_file_message_prefix" in module_text
    assert "EXTENSION_OPERATION_METADATA.not_file_message_prefix" in module_text
    assert 'prefix="Extension file not found at path"' not in module_text
    assert 'prefix="Extension file path must point to a file"' not in module_text
