from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_sync_profile_manager_uses_shared_request_helpers():
    module_text = Path("hyperbrowser/client/managers/sync_manager/profile.py").read_text(
        encoding="utf-8"
    )
    assert "create_profile_resource(" in module_text
    assert "get_profile_resource(" in module_text
    assert "delete_profile_resource(" in module_text
    assert "list_profile_resources(" in module_text
    assert "_client.transport.post(" not in module_text
    assert "_client.transport.get(" not in module_text
    assert "_client.transport.delete(" not in module_text
    assert "parse_response_model(" not in module_text


def test_async_profile_manager_uses_shared_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/async_manager/profile.py"
    ).read_text(encoding="utf-8")
    assert "create_profile_resource_async(" in module_text
    assert "get_profile_resource_async(" in module_text
    assert "delete_profile_resource_async(" in module_text
    assert "list_profile_resources_async(" in module_text
    assert "_client.transport.post(" not in module_text
    assert "_client.transport.get(" not in module_text
    assert "_client.transport.delete(" not in module_text
    assert "parse_response_model(" not in module_text
