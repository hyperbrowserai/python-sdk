from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


ARCHITECTURE_GUARD_MODULES = (
    "tests/test_agent_examples_coverage.py",
    "tests/test_agent_helper_boundary.py",
    "tests/test_agent_operation_metadata_usage.py",
    "tests/test_agent_payload_helper_usage.py",
    "tests/test_agent_request_internal_reuse.py",
    "tests/test_agent_route_builder_usage.py",
    "tests/test_agent_start_helper_usage.py",
    "tests/test_agent_task_read_helper_usage.py",
    "tests/test_agent_stop_helper_usage.py",
    "tests/test_agent_terminal_status_helper_usage.py",
    "tests/test_guardrail_ast_utils.py",
    "tests/test_manager_model_dump_usage.py",
    "tests/test_manager_helper_import_boundary.py",
    "tests/test_manager_parse_boundary.py",
    "tests/test_manager_transport_boundary.py",
    "tests/test_mapping_reader_usage.py",
    "tests/test_mapping_keys_access_usage.py",
    "tests/test_model_request_internal_reuse.py",
    "tests/test_tool_mapping_reader_usage.py",
    "tests/test_display_helper_usage.py",
    "tests/test_binary_file_open_helper_usage.py",
    "tests/test_browser_use_payload_helper_usage.py",
    "tests/test_ci_workflow_quality_gates.py",
    "tests/test_default_terminal_status_helper_usage.py",
    "tests/test_makefile_quality_targets.py",
    "tests/test_pyproject_architecture_marker.py",
    "tests/test_architecture_marker_usage.py",
    "tests/test_default_serialization_helper_usage.py",
    "tests/test_page_params_helper_usage.py",
    "tests/test_plain_type_guard_usage.py",
    "tests/test_plain_type_identity_usage.py",
    "tests/test_polling_defaults_usage.py",
    "tests/test_plain_list_helper_usage.py",
    "tests/test_optional_serialization_helper_usage.py",
    "tests/test_profile_operation_metadata_usage.py",
    "tests/test_profile_request_helper_usage.py",
    "tests/test_profile_team_request_internal_reuse.py",
    "tests/test_profile_route_builder_usage.py",
    "tests/test_profile_route_constants_usage.py",
    "tests/test_type_utils_usage.py",
    "tests/test_polling_loop_usage.py",
    "tests/test_core_type_helper_usage.py",
    "tests/test_contributing_architecture_guard_listing.py",
    "tests/test_readme_examples_listing.py",
    "tests/test_request_helper_parse_import_boundary.py",
    "tests/test_request_helper_transport_boundary.py",
    "tests/test_response_parse_usage_boundary.py",
    "tests/test_examples_syntax.py",
    "tests/test_docs_python3_commands.py",
    "tests/test_extension_create_helper_usage.py",
    "tests/test_extract_payload_helper_usage.py",
    "tests/test_examples_naming_convention.py",
    "tests/test_extension_operation_metadata_usage.py",
    "tests/test_extension_request_helper_usage.py",
    "tests/test_extension_request_internal_reuse.py",
    "tests/test_extension_route_constants_usage.py",
    "tests/test_job_pagination_helper_usage.py",
    "tests/test_job_fetch_helper_boundary.py",
    "tests/test_job_fetch_helper_usage.py",
    "tests/test_job_operation_metadata_usage.py",
    "tests/test_job_poll_helper_boundary.py",
    "tests/test_job_poll_helper_usage.py",
    "tests/test_job_request_internal_reuse.py",
    "tests/test_job_route_builder_usage.py",
    "tests/test_job_route_constants_usage.py",
    "tests/test_job_request_helper_usage.py",
    "tests/test_job_start_payload_helper_usage.py",
    "tests/test_job_query_params_helper_usage.py",
    "tests/test_job_wait_helper_boundary.py",
    "tests/test_job_wait_helper_usage.py",
    "tests/test_example_sync_async_parity.py",
    "tests/test_example_run_instructions.py",
    "tests/test_computer_action_endpoint_helper_usage.py",
    "tests/test_computer_action_operation_metadata_usage.py",
    "tests/test_computer_action_payload_helper_usage.py",
    "tests/test_computer_action_request_helper_usage.py",
    "tests/test_computer_action_request_internal_reuse.py",
    "tests/test_schema_injection_helper_usage.py",
    "tests/test_session_operation_metadata_usage.py",
    "tests/test_session_parse_usage_boundary.py",
    "tests/test_session_request_internal_reuse.py",
    "tests/test_session_route_constants_usage.py",
    "tests/test_session_request_helper_usage.py",
    "tests/test_session_profile_update_helper_usage.py",
    "tests/test_session_upload_helper_usage.py",
    "tests/test_start_and_wait_default_constants_usage.py",
    "tests/test_start_job_context_helper_usage.py",
    "tests/test_started_job_helper_boundary.py",
    "tests/test_team_operation_metadata_usage.py",
    "tests/test_team_request_helper_usage.py",
    "tests/test_team_route_constants_usage.py",
    "tests/test_web_operation_metadata_usage.py",
    "tests/test_web_pagination_internal_reuse.py",
    "tests/test_web_payload_helper_usage.py",
    "tests/test_web_fetch_search_usage.py",
    "tests/test_web_request_internal_reuse.py",
    "tests/test_web_request_helper_usage.py",
    "tests/test_web_route_constants_usage.py",
)


def test_architecture_guard_modules_are_marked():
    for module_path in ARCHITECTURE_GUARD_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "pytestmark = pytest.mark.architecture" in module_text


def test_architecture_guard_module_list_stays_in_sync_with_marker_files():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "pytestmark = pytest.mark.architecture" not in module_text:
            continue
        discovered_modules.append(module_path.as_posix())

    assert sorted(ARCHITECTURE_GUARD_MODULES) == discovered_modules
