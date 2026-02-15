from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

SESSION_UTILS_MODULE = Path("hyperbrowser/client/managers/session_utils.py")


def test_session_utils_uses_shared_parse_helpers():
    module_text = SESSION_UTILS_MODULE.read_text(encoding="utf-8")

    assert "parse_response_model(" in module_text
    assert "read_plain_list_items(" in module_text
    assert "parse_mapping_list_items(" in module_text
