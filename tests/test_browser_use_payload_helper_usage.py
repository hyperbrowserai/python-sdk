from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/agents/browser_use.py",
    "hyperbrowser/client/managers/async_manager/agents/browser_use.py",
)


def test_browser_use_managers_use_shared_payload_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_browser_use_start_payload(" in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
        assert "resolve_schema_input(" not in module_text
