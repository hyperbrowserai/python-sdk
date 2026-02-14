from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


AST_FUNCTION_SOURCE_GUARD_MODULES = (
    "tests/test_agent_request_wrapper_internal_reuse.py",
    "tests/test_job_request_route_builder_internal_reuse.py",
    "tests/test_job_request_wrapper_internal_reuse.py",
    "tests/test_model_request_function_parse_boundary.py",
    "tests/test_model_request_function_transport_boundary.py",
    "tests/test_model_request_wrapper_internal_reuse.py",
    "tests/test_request_wrapper_internal_reuse.py",
    "tests/test_session_recordings_follow_redirects_boundary.py",
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
        if "def _collect_function_sources" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []
