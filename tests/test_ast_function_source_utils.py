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


def test_collect_function_sources_returns_top_level_functions_only(tmp_path):
    module_path = tmp_path / "sample_module.py"
    module_path.write_text(
        "def top_level():\n"
        "    return 'ok'\n\n"
        "class Example:\n"
        "    def method(self):\n"
        "        return 'method'\n\n"
        "def wrapper():\n"
        "    def nested():\n"
        "        return 'nested'\n"
        "    return nested()\n",
        encoding="utf-8",
    )

    function_sources = collect_function_sources(str(module_path))

    assert sorted(function_sources.keys()) == ["top_level", "wrapper"]
