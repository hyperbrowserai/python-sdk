from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGER_MODULES = (
    "hyperbrowser/client/managers/sync_manager/profile.py",
    "hyperbrowser/client/managers/async_manager/profile.py",
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
)


def test_profile_and_session_managers_use_optional_serialization_helper():
    for module_path in MANAGER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "serialize_optional_model_dump_to_dict(" in module_text
        assert "payload = {}" not in module_text
