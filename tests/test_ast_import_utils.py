import pytest

from tests.ast_import_utils import imports_collect_function_sources

pytestmark = pytest.mark.architecture


def test_imports_collect_function_sources_detects_expected_import():
    module_text = (
        "from tests.ast_function_source_utils import collect_function_sources\n"
        "collect_function_sources('tests/test_job_request_wrapper_internal_reuse.py')\n"
    )

    assert imports_collect_function_sources(module_text) is True


def test_imports_collect_function_sources_ignores_non_matching_imports():
    module_text = (
        "from tests.ast_function_source_utils import something_else\n"
        "from tests.other_helper import collect_function_sources\n"
    )

    assert imports_collect_function_sources(module_text) is False


def test_imports_collect_function_sources_supports_aliased_import():
    module_text = (
        "from tests.ast_function_source_utils import collect_function_sources as cfs\n"
        "cfs('tests/test_model_request_wrapper_internal_reuse.py')\n"
    )

    assert imports_collect_function_sources(module_text) is True


def test_imports_collect_function_sources_ignores_non_from_imports():
    module_text = (
        "import tests.ast_function_source_utils as source_utils\n"
        "source_utils.collect_function_sources('tests/test_web_request_wrapper_internal_reuse.py')\n"
    )

    assert imports_collect_function_sources(module_text) is False
