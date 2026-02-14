from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


WEB_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/__init__.py",
    "hyperbrowser/client/managers/async_manager/web/__init__.py",
)


def test_web_managers_use_shared_payload_helpers():
    for module_path in WEB_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_web_fetch_payload(" in module_text
        assert "build_web_search_payload(" in module_text
        assert "inject_web_output_schemas(" not in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
