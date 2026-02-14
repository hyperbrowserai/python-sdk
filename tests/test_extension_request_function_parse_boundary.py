import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/extension_request_utils.py"

CREATE_WRAPPERS = (
    "create_extension_resource",
    "create_extension_resource_async",
)

LIST_WRAPPERS = (
    "list_extension_resources",
    "list_extension_resources_async",
)


def test_extension_create_wrappers_do_not_call_extension_list_parser():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in CREATE_WRAPPERS:
        function_source = function_sources[function_name]
        assert "parse_extension_list_response_data(" not in function_source


def test_extension_list_wrappers_call_extension_list_parser():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in LIST_WRAPPERS:
        function_source = function_sources[function_name]
        assert "parse_extension_list_response_data(" in function_source
