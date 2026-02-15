from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

EXTENSION_UTILS_MODULE = Path("hyperbrowser/client/managers/extension_utils.py")


def test_extension_utils_uses_format_string_key_for_error():
    module_text = EXTENSION_UTILS_MODULE.read_text(encoding="utf-8")

    assert "format_string_key_for_error(" in module_text
    assert "_MAX_DISPLAYED_MISSING_KEY_LENGTH" in module_text
    assert "_safe_stringify_key(" in module_text
