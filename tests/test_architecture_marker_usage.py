from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


ARCHITECTURE_GUARD_MODULES = (
    "tests/test_guardrail_ast_utils.py",
    "tests/test_manager_model_dump_usage.py",
    "tests/test_mapping_reader_usage.py",
    "tests/test_mapping_keys_access_usage.py",
    "tests/test_tool_mapping_reader_usage.py",
    "tests/test_display_helper_usage.py",
    "tests/test_ci_workflow_quality_gates.py",
    "tests/test_makefile_quality_targets.py",
    "tests/test_pyproject_architecture_marker.py",
    "tests/test_architecture_marker_usage.py",
    "tests/test_default_serialization_helper_usage.py",
    "tests/test_plain_type_guard_usage.py",
    "tests/test_plain_type_identity_usage.py",
    "tests/test_plain_list_helper_usage.py",
    "tests/test_optional_serialization_helper_usage.py",
    "tests/test_type_utils_usage.py",
    "tests/test_polling_loop_usage.py",
    "tests/test_core_type_helper_usage.py",
    "tests/test_contributing_architecture_guard_listing.py",
    "tests/test_readme_examples_listing.py",
    "tests/test_examples_syntax.py",
    "tests/test_docs_python3_commands.py",
    "tests/test_examples_naming_convention.py",
    "tests/test_job_pagination_helper_usage.py",
    "tests/test_example_sync_async_parity.py",
    "tests/test_example_run_instructions.py",
    "tests/test_computer_action_endpoint_helper_usage.py",
    "tests/test_session_upload_helper_usage.py",
    "tests/test_web_payload_helper_usage.py",
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
