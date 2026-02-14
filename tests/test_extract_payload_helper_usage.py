from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/extract.py",
    "hyperbrowser/client/managers/async_manager/extract.py",
)


def test_extract_managers_use_shared_extract_payload_helper():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "build_extract_start_payload(" in module_text
        assert "Either schema or prompt must be provided" not in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
        assert "resolve_schema_input(" not in module_text
