from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/sync_manager/web/__init__.py",
    "hyperbrowser/client/managers/async_manager/web/__init__.py",
)


def test_web_managers_use_shared_fetch_search_route_and_metadata_constants():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "web_route_constants import WEB_FETCH_ROUTE_PATH, WEB_SEARCH_ROUTE_PATH" in module_text
        assert "web_operation_metadata import WEB_REQUEST_OPERATION_METADATA" in module_text
        assert "_FETCH_ROUTE_PATH = WEB_FETCH_ROUTE_PATH" in module_text
        assert "_SEARCH_ROUTE_PATH = WEB_SEARCH_ROUTE_PATH" in module_text
        assert "_OPERATION_METADATA = WEB_REQUEST_OPERATION_METADATA" in module_text
        assert '"/web/fetch"' not in module_text
        assert '"/web/search"' not in module_text
        assert 'operation_name="web fetch"' not in module_text
        assert 'operation_name="web search"' not in module_text


def test_web_managers_use_shared_fetch_search_request_helpers():
    sync_text = Path("hyperbrowser/client/managers/sync_manager/web/__init__.py").read_text(
        encoding="utf-8"
    )
    async_text = Path("hyperbrowser/client/managers/async_manager/web/__init__.py").read_text(
        encoding="utf-8"
    )

    assert "start_web_job(" in sync_text
    assert "_client.transport.post(" not in sync_text
    assert "parse_response_model(" not in sync_text

    assert "start_web_job_async(" in async_text
    assert "_client.transport.post(" not in async_text
    assert "parse_response_model(" not in async_text
