import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


EXPECTED_AST_FUNCTION_SOURCE_IMPORTER_MODULES = (
    "tests/test_agent_request_wrapper_internal_reuse.py",
    "tests/test_ast_function_source_utils.py",
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

def _imports_collect_function_sources(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "tests.ast_function_source_utils":
            continue
        if any(alias.name == "collect_function_sources" for alias in node.names):
            return True
    return False


def test_ast_function_source_helper_imports_are_centralized():
    discovered_modules: list[str] = []
    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if not _imports_collect_function_sources(module_text):
            continue
        discovered_modules.append(module_path.as_posix())

    assert discovered_modules == list(EXPECTED_AST_FUNCTION_SOURCE_IMPORTER_MODULES)
