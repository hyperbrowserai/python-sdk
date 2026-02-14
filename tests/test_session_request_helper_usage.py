from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_sync_session_manager_uses_shared_request_helpers():
    module_text = Path("hyperbrowser/client/managers/sync_manager/session.py").read_text(
        encoding="utf-8"
    )
    assert "get_session_model(" in module_text
    assert "get_session_recordings(" in module_text
    assert "post_session_model(" in module_text
    assert "put_session_model(" in module_text
    assert "_client.transport.get(" not in module_text
    assert "_client.transport.post(" not in module_text
    assert "_client.transport.put(" not in module_text
    assert "parse_session_response_model(" not in module_text
    assert "parse_session_recordings_response_data(" not in module_text


def test_async_session_manager_uses_shared_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/async_manager/session.py"
    ).read_text(encoding="utf-8")
    assert "get_session_model_async(" in module_text
    assert "get_session_recordings_async(" in module_text
    assert "post_session_model_async(" in module_text
    assert "put_session_model_async(" in module_text
    assert "_client.transport.get(" not in module_text
    assert "_client.transport.post(" not in module_text
    assert "_client.transport.put(" not in module_text
    assert "parse_session_response_model(" not in module_text
    assert "parse_session_recordings_response_data(" not in module_text
