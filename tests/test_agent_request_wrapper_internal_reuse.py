import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_WRAPPER_EXPECTATIONS = {
    "hyperbrowser/client/managers/agent_start_utils.py": {
        "start_agent_task": ("start_job(",),
        "start_agent_task_async": ("start_job_async(",),
    },
    "hyperbrowser/client/managers/agent_task_read_utils.py": {
        "get_agent_task": ("get_job(",),
        "get_agent_task_status": ("get_job_status(",),
        "get_agent_task_async": ("get_job_async(",),
        "get_agent_task_status_async": ("get_job_status_async(",),
    },
    "hyperbrowser/client/managers/agent_stop_utils.py": {
        "stop_agent_task": ("put_job_action(", 'action_suffix="/stop"'),
        "stop_agent_task_async": ("put_job_action_async(", 'action_suffix="/stop"'),
    },
}


def test_agent_request_wrappers_delegate_to_expected_job_helpers():
    for module_path, wrapper_expectations in MODULE_WRAPPER_EXPECTATIONS.items():
        function_sources = collect_function_sources(module_path)
        for wrapper_name, expected_markers in wrapper_expectations.items():
            wrapper_source = function_sources[wrapper_name]
            for expected_marker in expected_markers:
                assert expected_marker in wrapper_source
            assert "client.transport." not in wrapper_source
            assert "parse_response_model(" not in wrapper_source
