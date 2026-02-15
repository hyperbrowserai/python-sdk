from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

LIST_PARSING_MODULE = Path("hyperbrowser/client/managers/list_parsing_utils.py")


def test_list_parsing_uses_safe_key_display_helper():
    module_text = LIST_PARSING_MODULE.read_text(encoding="utf-8")

    assert "safe_key_display_for_error(" in module_text
    assert "key_display=key_display" in module_text
    assert "read_value_error_builder=lambda key_text" in module_text
