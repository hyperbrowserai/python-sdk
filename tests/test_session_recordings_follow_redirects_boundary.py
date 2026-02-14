import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/session_request_utils.py"


def test_sync_session_recordings_wrapper_enforces_follow_redirects():
    function_source = collect_function_sources(MODULE_PATH)["get_session_recordings"]
    assert "get_session_resource(" in function_source
    assert "follow_redirects=True" in function_source


def test_async_session_recordings_wrapper_enforces_follow_redirects():
    function_source = collect_function_sources(MODULE_PATH)["get_session_recordings_async"]
    assert "get_session_resource_async(" in function_source
    assert "follow_redirects=True" in function_source
