import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = Path("hyperbrowser/client/managers/job_request_utils.py")

SYNC_WRAPPER_TO_MODEL_HELPER = {
    "start_job": "post_model_request(",
    "get_job_status": "get_model_request(",
    "get_job": "get_model_request(",
    "put_job_action": "put_model_request(",
}

ASYNC_WRAPPER_TO_MODEL_HELPER = {
    "start_job_async": "post_model_request_async(",
    "get_job_status_async": "get_model_request_async(",
    "get_job_async": "get_model_request_async(",
    "put_job_action_async": "put_model_request_async(",
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


def test_sync_job_request_wrappers_delegate_to_model_helpers():
    function_sources = _collect_function_sources()
    for wrapper_name, helper_call in SYNC_WRAPPER_TO_MODEL_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
        assert "parse_response_model(" not in wrapper_source


def test_async_job_request_wrappers_delegate_to_model_helpers():
    function_sources = _collect_function_sources()
    for wrapper_name, helper_call in ASYNC_WRAPPER_TO_MODEL_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
        assert "parse_response_model(" not in wrapper_source
