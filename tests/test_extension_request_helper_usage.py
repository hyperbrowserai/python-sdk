from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_sync_extension_manager_uses_shared_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/sync_manager/extension.py"
    ).read_text(encoding="utf-8")
    assert "create_extension_resource(" in module_text
    assert "list_extension_resources(" in module_text
    assert "_client.transport.post(" not in module_text
    assert "_client.transport.get(" not in module_text
    assert "parse_response_model(" not in module_text


def test_async_extension_manager_uses_shared_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/async_manager/extension.py"
    ).read_text(encoding="utf-8")
    assert "create_extension_resource_async(" in module_text
    assert "list_extension_resources_async(" in module_text
    assert "_client.transport.post(" not in module_text
    assert "_client.transport.get(" not in module_text
    assert "parse_response_model(" not in module_text
