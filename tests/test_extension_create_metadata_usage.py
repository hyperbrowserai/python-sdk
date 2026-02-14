import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/extension_create_utils.py"


def test_extension_create_helper_uses_shared_operation_metadata_prefixes():
    module_text = Path(MODULE_PATH).read_text(encoding="utf-8")

    assert "extension_operation_metadata import" in module_text
    assert "EXTENSION_OPERATION_METADATA.missing_file_message_prefix" in module_text
    assert "EXTENSION_OPERATION_METADATA.not_file_message_prefix" in module_text
    assert "EXTENSION_DEFAULT_MISSING_FILE_MESSAGE_PREFIX" in module_text
    assert "EXTENSION_DEFAULT_NOT_FILE_MESSAGE_PREFIX" in module_text
    assert (
        re.search(
            r'(?<!default_)prefix="Extension file not found at path"',
            module_text,
        )
        is None
    )
    assert (
        re.search(
            r'(?<!default_)prefix="Extension file path must point to a file"',
            module_text,
        )
        is None
    )
