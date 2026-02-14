import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = Path("hyperbrowser/client/managers/session_request_utils.py")

SYNC_PARSED_WRAPPER_TO_RESOURCE_HELPER = {
    "post_session_model": "post_session_resource(",
    "get_session_model": "get_session_resource(",
    "put_session_model": "put_session_resource(",
    "get_session_recordings": "get_session_resource(",
}

ASYNC_PARSED_WRAPPER_TO_RESOURCE_HELPER = {
    "post_session_model_async": "post_session_resource_async(",
    "get_session_model_async": "get_session_resource_async(",
    "put_session_model_async": "put_session_resource_async(",
    "get_session_recordings_async": "get_session_resource_async(",
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


def test_sync_parsed_session_wrappers_delegate_to_resource_helpers():
    function_sources = _collect_function_sources()
    for wrapper_name, helper_call in SYNC_PARSED_WRAPPER_TO_RESOURCE_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source


def test_async_parsed_session_wrappers_delegate_to_resource_helpers():
    function_sources = _collect_function_sources()
    for wrapper_name, helper_call in ASYNC_PARSED_WRAPPER_TO_RESOURCE_HELPER.items():
        wrapper_source = function_sources[wrapper_name]
        assert helper_call in wrapper_source
        assert "client.transport." not in wrapper_source
