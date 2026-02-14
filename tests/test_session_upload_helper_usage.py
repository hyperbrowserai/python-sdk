from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


SESSION_MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
)


def test_session_managers_use_shared_upload_input_normalizer():
    for module_path in SESSION_MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "normalize_upload_file_input(" in module_text
        assert "os.fspath(" not in module_text
        assert "ensure_existing_file_path(" not in module_text
        assert 'getattr(file_input, "read"' not in module_text
