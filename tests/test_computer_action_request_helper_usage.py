from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_sync_computer_action_manager_uses_request_helper():
    module_text = Path(
        "hyperbrowser/client/managers/sync_manager/computer_action.py"
    ).read_text(encoding="utf-8")
    assert "execute_computer_action_request(" in module_text
    assert "_client.transport.post(" not in module_text
    assert "parse_response_model(" not in module_text


def test_async_computer_action_manager_uses_request_helper():
    module_text = Path(
        "hyperbrowser/client/managers/async_manager/computer_action.py"
    ).read_text(encoding="utf-8")
    assert "execute_computer_action_request_async(" in module_text
    assert "_client.transport.post(" not in module_text
    assert "parse_response_model(" not in module_text
