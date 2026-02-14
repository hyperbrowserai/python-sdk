import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


MODULE_PATH = "hyperbrowser/client/managers/session_request_utils.py"

PARSED_SESSION_MODEL_WRAPPERS = (
    "post_session_model",
    "get_session_model",
    "put_session_model",
    "post_session_model_async",
    "get_session_model_async",
    "put_session_model_async",
)

SESSION_RECORDINGS_WRAPPERS = (
    "get_session_recordings",
    "get_session_recordings_async",
)

RESOURCE_HELPERS = (
    "post_session_resource",
    "get_session_resource",
    "put_session_resource",
    "post_session_resource_async",
    "get_session_resource_async",
    "put_session_resource_async",
)


def test_parsed_session_model_wrappers_call_session_model_parser():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in PARSED_SESSION_MODEL_WRAPPERS:
        function_source = function_sources[function_name]
        assert "parse_session_response_model(" in function_source


def test_session_recordings_wrappers_call_recordings_parser():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in SESSION_RECORDINGS_WRAPPERS:
        function_source = function_sources[function_name]
        assert "parse_session_recordings_response_data(" in function_source


def test_resource_helpers_do_not_call_session_parsers():
    function_sources = collect_function_sources(MODULE_PATH)
    for function_name in RESOURCE_HELPERS:
        function_source = function_sources[function_name]
        assert "parse_session_response_model(" not in function_source
        assert "parse_session_recordings_response_data(" not in function_source
