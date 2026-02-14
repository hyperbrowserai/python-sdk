import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/session_request_utils.py"

SYNC_RESOURCE_WRAPPER_TO_MODEL_HELPER = {
    "post_session_resource": "post_model_response_data(",
    "get_session_resource": "get_model_response_data(",
    "put_session_resource": "put_model_response_data(",
}

ASYNC_RESOURCE_WRAPPER_TO_MODEL_HELPER = {
    "post_session_resource_async": "post_model_response_data_async(",
    "get_session_resource_async": "get_model_response_data_async(",
    "put_session_resource_async": "put_model_response_data_async(",
}

def test_sync_session_resource_wrappers_delegate_to_model_helpers():
    function_sources = collect_function_sources(MODULE_PATH)
    for wrapper_name, helper_call in SYNC_RESOURCE_WRAPPER_TO_MODEL_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source


def test_async_session_resource_wrappers_delegate_to_model_helpers():
    function_sources = collect_function_sources(MODULE_PATH)
    for wrapper_name, helper_call in ASYNC_RESOURCE_WRAPPER_TO_MODEL_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
