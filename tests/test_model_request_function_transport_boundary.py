import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = Path("hyperbrowser/client/managers/model_request_utils.py")

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


def _collect_function_sources() -> dict[str, str]:
    module_text = MODULE_PATH.read_text(encoding="utf-8")
    module_ast = ast.parse(module_text)
    function_sources: dict[str, str] = {}
    for node in module_ast.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_source = ast.get_source_segment(module_text, node)
            if function_source is not None:
                function_sources[node.name] = function_source
    return function_sources


def test_parsed_model_request_wrappers_do_not_call_transport_directly():
    function_sources = _collect_function_sources()
    for function_name in PARSED_WRAPPER_FUNCTIONS:
        function_source = function_sources[function_name]
        assert "client.transport." not in function_source


def test_raw_model_request_helpers_are_transport_boundary():
    function_sources = _collect_function_sources()
    for function_name in RAW_HELPER_FUNCTIONS:
        function_source = function_sources[function_name]
        assert "client.transport." in function_source
