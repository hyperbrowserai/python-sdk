import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/job_request_utils.py"

FUNCTION_ROUTE_BUILDER_EXPECTATIONS = {
    "get_job_status": "build_job_status_route(",
    "get_job": "build_job_route(",
    "put_job_action": "build_job_action_route(",
    "get_job_status_async": "build_job_status_route(",
    "get_job_async": "build_job_route(",
    "put_job_action_async": "build_job_action_route(",
}

def test_job_request_wrappers_use_expected_route_builders():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name, route_builder_call in FUNCTION_ROUTE_BUILDER_EXPECTATIONS.items():
        function_source = function_sources[function_name]
        assert route_builder_call in function_source
