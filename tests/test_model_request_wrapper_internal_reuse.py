import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/model_request_utils.py"

SYNC_PARSED_WRAPPER_TO_RAW_HELPER = {
    "post_model_request": "post_model_response_data(",
    "get_model_request": "get_model_response_data(",
    "delete_model_request": "delete_model_response_data(",
    "put_model_request": "put_model_response_data(",
    "post_model_request_to_endpoint": "post_model_response_data_to_endpoint(",
}

ASYNC_PARSED_WRAPPER_TO_RAW_HELPER = {
    "post_model_request_async": "post_model_response_data_async(",
    "get_model_request_async": "get_model_response_data_async(",
    "delete_model_request_async": "delete_model_response_data_async(",
    "put_model_request_async": "put_model_response_data_async(",
    "post_model_request_to_endpoint_async": "post_model_response_data_to_endpoint_async(",
}

def test_sync_parsed_wrappers_delegate_to_raw_helpers():
    function_sources = collect_function_sources(MODULE_PATH)
    for wrapper_name, raw_helper_call in SYNC_PARSED_WRAPPER_TO_RAW_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert raw_helper_call in wrapper_source
        assert "client.transport." not in wrapper_source


def test_async_parsed_wrappers_delegate_to_raw_helpers():
    function_sources = collect_function_sources(MODULE_PATH)
    for wrapper_name, raw_helper_call in ASYNC_PARSED_WRAPPER_TO_RAW_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert raw_helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
