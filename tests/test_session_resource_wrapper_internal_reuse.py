import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = Path("hyperbrowser/client/managers/session_request_utils.py")

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


def test_sync_session_resource_wrappers_delegate_to_model_helpers():
    function_sources = _collect_function_sources()
    for wrapper_name, helper_call in SYNC_RESOURCE_WRAPPER_TO_MODEL_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source


def test_async_session_resource_wrappers_delegate_to_model_helpers():
    function_sources = _collect_function_sources()
    for wrapper_name, helper_call in ASYNC_RESOURCE_WRAPPER_TO_MODEL_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
