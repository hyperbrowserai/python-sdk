import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULE_PATH = Path("hyperbrowser/client/managers/job_request_utils.py")

FUNCTION_ROUTE_BUILDER_EXPECTATIONS = {
    "get_job_status": "build_job_status_route(",
    "get_job": "build_job_route(",
    "put_job_action": "build_job_action_route(",
    "get_job_status_async": "build_job_status_route(",
    "get_job_async": "build_job_route(",
    "put_job_action_async": "build_job_action_route(",
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


def test_job_request_wrappers_use_expected_route_builders():
    function_sources = _collect_function_sources()
    for function_name, route_builder_call in FUNCTION_ROUTE_BUILDER_EXPECTATIONS.items():
        function_source = function_sources[function_name]
        assert route_builder_call in function_source
