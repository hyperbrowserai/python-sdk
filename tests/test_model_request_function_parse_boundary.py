import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/model_request_utils.py"

PARSED_WRAPPER_FUNCTIONS = (
    "post_model_request",
    "get_model_request",
    "delete_model_request",
    "put_model_request",
    "post_model_request_async",
    "get_model_request_async",
    "delete_model_request_async",
    "put_model_request_async",
    "post_model_request_to_endpoint",
    "post_model_request_to_endpoint_async",
)

RAW_HELPER_FUNCTIONS = (
    "post_model_response_data",
    "get_model_response_data",
    "delete_model_response_data",
    "put_model_response_data",
    "post_model_response_data_async",
    "get_model_response_data_async",
    "delete_model_response_data_async",
    "put_model_response_data_async",
    "post_model_response_data_to_endpoint",
    "post_model_response_data_to_endpoint_async",
)


def test_parsed_model_request_wrappers_call_parse_response_model():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in PARSED_WRAPPER_FUNCTIONS:
        function_source = function_sources[function_name]
        assert "parse_response_model(" in function_source


def test_raw_model_request_helpers_do_not_call_parse_response_model():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in RAW_HELPER_FUNCTIONS:
        function_source = function_sources[function_name]
        assert "parse_response_model(" not in function_source
