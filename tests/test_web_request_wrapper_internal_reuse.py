import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/web_request_utils.py"

SYNC_WRAPPER_TO_JOB_HELPER = {
    "start_web_job": "start_job(",
    "get_web_job_status": "get_job_status(",
    "get_web_job": "get_job(",
}

ASYNC_WRAPPER_TO_JOB_HELPER = {
    "start_web_job_async": "start_job_async(",
    "get_web_job_status_async": "get_job_status_async(",
    "get_web_job_async": "get_job_async(",
}


def test_sync_web_request_wrappers_delegate_to_job_helpers():
    function_sources = collect_function_sources(MODULE_PATH)
    for wrapper_name, helper_call in SYNC_WRAPPER_TO_JOB_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
        assert "parse_response_model(" not in wrapper_source


def test_async_web_request_wrappers_delegate_to_job_helpers():
    function_sources = collect_function_sources(MODULE_PATH)
    for wrapper_name, helper_call in ASYNC_WRAPPER_TO_JOB_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
        assert "parse_response_model(" not in wrapper_source
