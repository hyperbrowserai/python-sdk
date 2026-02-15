from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

SESSION_UTILS_MODULE = Path("hyperbrowser/client/managers/session_utils.py")


def test_session_utils_uses_format_string_key_for_error():
    module_text = SESSION_UTILS_MODULE.read_text(encoding="utf-8")

    assert "format_string_key_for_error(" in module_text
    assert "_MAX_KEY_DISPLAY_LENGTH" in module_text
    assert "_format_recording_key_display(" in module_text
    assert "max_length=_MAX_KEY_DISPLAY_LENGTH" in module_text
    assert "parse_mapping_list_items(" in module_text
    assert "key_display=_format_recording_key_display" in module_text
