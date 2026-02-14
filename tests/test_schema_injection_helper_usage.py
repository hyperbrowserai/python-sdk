from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/browser_use_payload_utils.py",
    "hyperbrowser/client/managers/extract_payload_utils.py",
)


def test_payload_utils_use_shared_schema_injection_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "inject_resolved_schema(" in module_text
        assert "resolve_schema_input(" not in module_text
