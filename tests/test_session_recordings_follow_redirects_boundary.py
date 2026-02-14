import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = Path("hyperbrowser/client/managers/session_request_utils.py")


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


def test_sync_session_recordings_wrapper_enforces_follow_redirects():
    function_source = _collect_function_sources()["get_session_recordings"]
    assert "get_session_resource(" in function_source
    assert "follow_redirects=True" in function_source


def test_async_session_recordings_wrapper_enforces_follow_redirects():
    function_source = _collect_function_sources()["get_session_recordings_async"]
    assert "get_session_resource_async(" in function_source
    assert "follow_redirects=True" in function_source
