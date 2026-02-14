import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/profile_request_utils.py"

PROFILE_ID_WRAPPERS = (
    "get_profile_resource",
    "delete_profile_resource",
    "get_profile_resource_async",
    "delete_profile_resource_async",
)

NON_PROFILE_ID_WRAPPERS = (
    "create_profile_resource",
    "list_profile_resources",
    "create_profile_resource_async",
    "list_profile_resources_async",
)


def test_profile_id_wrappers_use_profile_route_builder():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in PROFILE_ID_WRAPPERS:
        function_source = function_sources[function_name]
        assert "build_profile_route(profile_id)" in function_source


def test_non_profile_id_wrappers_do_not_use_profile_route_builder():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in NON_PROFILE_ID_WRAPPERS:
        function_source = function_sources[function_name]
        assert "build_profile_route(profile_id)" not in function_source
