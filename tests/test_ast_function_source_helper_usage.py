from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


AST_FUNCTION_SOURCE_GUARD_MODULES = (
    "tests/test_agent_request_wrapper_internal_reuse.py",
    "tests/test_extension_request_function_parse_boundary.py",
    "tests/test_job_request_route_builder_internal_reuse.py",
    "tests/test_job_request_wrapper_internal_reuse.py",
    "tests/test_model_request_function_parse_boundary.py",
    "tests/test_model_request_function_transport_boundary.py",
    "tests/test_model_request_wrapper_internal_reuse.py",
    "tests/test_request_wrapper_internal_reuse.py",
    "tests/test_session_recordings_follow_redirects_boundary.py",
    "tests/test_session_request_function_parse_boundary.py",
    "tests/test_session_request_wrapper_internal_reuse.py",
    "tests/test_session_resource_wrapper_internal_reuse.py",
    "tests/test_web_request_wrapper_internal_reuse.py",
)


def test_ast_guard_modules_reuse_shared_collect_function_sources_helper():
    violating_modules: list[str] = []
    for module_path in AST_FUNCTION_SOURCE_GUARD_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if "ast_function_source_utils import collect_function_sources" not in module_text:
            violating_modules.append(module_path)
            continue
        if "collect_function_sources(" not in module_text:
            violating_modules.append(module_path)
            continue
        if "def _collect_function_sources" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []


def test_ast_guard_inventory_stays_in_sync_with_helper_imports():
    excluded_modules = {
        "tests/test_ast_function_source_helper_usage.py",
        "tests/test_ast_function_source_utils.py",
    }
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        normalized_path = module_path.as_posix()
        if normalized_path in excluded_modules:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if "ast_function_source_utils import collect_function_sources" not in module_text:
            continue
        discovered_modules.append(normalized_path)

    assert sorted(AST_FUNCTION_SOURCE_GUARD_MODULES) == discovered_modules
