from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/extension_utils.py",
    "hyperbrowser/client/managers/session_utils.py",
)


def test_extension_and_session_utils_use_shared_plain_list_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "read_plain_list_items(" in module_text
        assert "type(extensions_value) is not list" not in module_text
        assert "type(response_data) is not list" not in module_text
