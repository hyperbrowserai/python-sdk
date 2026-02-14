from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXTENSION_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/extension.py",
    "hyperbrowser/client/managers/async_manager/extension.py",
)


def test_extension_managers_use_shared_extension_create_helper():
    for module_path in EXTENSION_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "normalize_extension_create_input(" in module_text
        assert "serialize_model_dump_to_dict(" not in module_text
        assert "ensure_existing_file_path(" not in module_text
        assert "params.file_path is invalid" not in module_text
