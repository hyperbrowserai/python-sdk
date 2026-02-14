import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_WRAPPER_EXPECTATIONS = {
    "hyperbrowser/client/managers/profile_request_utils.py": {
        "create_profile_resource": ("post_model_request(",),
        "get_profile_resource": ("get_model_request(",),
        "delete_profile_resource": ("delete_model_request(",),
        "list_profile_resources": ("get_model_request(",),
        "create_profile_resource_async": ("post_model_request_async(",),
        "get_profile_resource_async": ("get_model_request_async(",),
        "delete_profile_resource_async": ("delete_model_request_async(",),
        "list_profile_resources_async": ("get_model_request_async(",),
    },
    "hyperbrowser/client/managers/team_request_utils.py": {
        "get_team_resource": ("get_model_request(",),
        "get_team_resource_async": ("get_model_request_async(",),
    },
    "hyperbrowser/client/managers/computer_action_request_utils.py": {
        "execute_computer_action_request": ("post_model_request_to_endpoint(",),
        "execute_computer_action_request_async": (
            "post_model_request_to_endpoint_async(",
        ),
    },
    "hyperbrowser/client/managers/extension_request_utils.py": {
        "create_extension_resource": ("post_model_request(",),
        "create_extension_resource_async": ("post_model_request_async(",),
        "list_extension_resources": (
            "get_model_response_data(",
            "parse_extension_list_response_data(",
        ),
        "list_extension_resources_async": (
            "get_model_response_data_async(",
            "parse_extension_list_response_data(",
        ),
    },
}

def test_request_wrappers_delegate_to_expected_shared_helpers():
    for module_path, wrapper_expectations in MODULE_WRAPPER_EXPECTATIONS.items():
        function_sources = collect_function_sources(module_path)
        for wrapper_name, expected_markers in wrapper_expectations.items():
            wrapper_source = function_sources[wrapper_name]
            for expected_marker in expected_markers:
                assert expected_marker in wrapper_source
            assert "client.transport." not in wrapper_source
            assert "parse_response_model(" not in wrapper_source
