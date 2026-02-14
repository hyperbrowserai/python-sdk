from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_sync_team_manager_uses_shared_request_helper():
    module_text = Path("hyperbrowser/client/managers/sync_manager/team.py").read_text(
        encoding="utf-8"
    )
    assert "get_team_resource(" in module_text
    assert "_client.transport.get(" not in module_text
    assert "parse_response_model(" not in module_text


def test_async_team_manager_uses_shared_request_helper():
    module_text = Path("hyperbrowser/client/managers/async_manager/team.py").read_text(
        encoding="utf-8"
    )
    assert "get_team_resource_async(" in module_text
    assert "_client.transport.get(" not in module_text
    assert "parse_response_model(" not in module_text
