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
    "tests/test_plain_type_guard_usage.py",
    "tests/test_type_utils_usage.py",
    "tests/test_polling_loop_usage.py",
    "tests/test_core_type_helper_usage.py",
)


def test_architecture_guard_modules_are_marked():
    for module_path in ARCHITECTURE_GUARD_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "pytestmark = pytest.mark.architecture" in module_text
