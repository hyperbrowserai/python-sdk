import pytest

from tests.ast_function_source_utils import collect_function_sources

pytestmark = pytest.mark.architecture


def test_collect_function_sources_reads_sync_and_async_functions():
    function_sources = collect_function_sources(
        "hyperbrowser/client/managers/model_request_utils.py"
    )

    assert "post_model_request" in function_sources
    assert "def post_model_request(" in function_sources["post_model_request"]
    assert "post_model_response_data(" in function_sources["post_model_request"]

    assert "post_model_request_async" in function_sources
    assert "async def post_model_request_async(" in function_sources[
        "post_model_request_async"
    ]
    assert "post_model_response_data_async(" in function_sources[
        "post_model_request_async"
    ]
