import pytest

from tests.ast_import_utils import (
    calls_symbol,
    imports_collect_function_sources,
    imports_from_module,
    imports_imports_imports_collect_function_sources,
    imports_imports_collect_function_sources,
    imports_symbol_from_module,
)

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


def test_imports_from_module_detects_expected_from_import():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources\n"
        "imports_collect_function_sources('dummy')\n"
    )

    assert imports_from_module(module_text, module="tests.ast_import_utils") is True


def test_imports_from_module_detects_expected_direct_import():
    module_text = (
        "import tests.ast_import_utils as import_utils\n"
        "import_utils.imports_collect_function_sources('dummy')\n"
    )

    assert imports_from_module(module_text, module="tests.ast_import_utils") is True


def test_imports_from_module_ignores_unrelated_module_imports():
    module_text = (
        "from tests.ast_function_source_utils import collect_function_sources\n"
        "collect_function_sources('dummy')\n"
    )

    assert imports_from_module(module_text, module="tests.ast_import_utils") is False


def test_imports_symbol_from_module_detects_expected_symbol():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources\n"
        "imports_collect_function_sources('dummy')\n"
    )

    assert (
        imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="imports_collect_function_sources",
        )
        is True
    )


def test_imports_symbol_from_module_ignores_unrelated_symbols():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources\n"
        "from tests.ast_import_utils import imports_imports_collect_function_sources\n"
    )

    assert (
        imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="missing_symbol",
        )
        is False
    )


def test_imports_symbol_from_module_supports_aliased_symbol_import():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources as helper\n"
        "helper('dummy')\n"
    )

    assert (
        imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="imports_collect_function_sources",
        )
        is True
    )


def test_imports_symbol_from_module_ignores_non_from_import():
    module_text = (
        "import tests.ast_import_utils as import_utils\n"
        "import_utils.imports_collect_function_sources('dummy')\n"
    )

    assert (
        imports_symbol_from_module(
            module_text,
            module="tests.ast_import_utils",
            symbol="imports_collect_function_sources",
        )
        is False
    )


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


def test_imports_imports_collect_function_sources_detects_expected_import():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources\n"
        "imports_collect_function_sources('dummy')\n"
    )

    assert imports_imports_collect_function_sources(module_text) is True


def test_imports_imports_collect_function_sources_ignores_non_matching_imports():
    module_text = (
        "from tests.ast_import_utils import other_helper\n"
        "from tests.ast_function_source_utils import imports_collect_function_sources\n"
    )

    assert imports_imports_collect_function_sources(module_text) is False


def test_imports_imports_collect_function_sources_supports_aliased_import():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources as helper\n"
        "helper('dummy')\n"
    )

    assert imports_imports_collect_function_sources(module_text) is True


def test_imports_imports_collect_function_sources_ignores_non_from_imports():
    module_text = (
        "import tests.ast_import_utils as import_utils\n"
        "import_utils.imports_collect_function_sources('dummy')\n"
    )

    assert imports_imports_collect_function_sources(module_text) is False


def test_imports_imports_imports_collect_function_sources_detects_expected_import():
    module_text = (
        "from tests.ast_import_utils import imports_imports_collect_function_sources\n"
        "imports_imports_collect_function_sources('dummy')\n"
    )

    assert imports_imports_imports_collect_function_sources(module_text) is True


def test_imports_imports_imports_collect_function_sources_ignores_non_matching_imports():
    module_text = (
        "from tests.ast_import_utils import imports_collect_function_sources\n"
        "imports_collect_function_sources('dummy')\n"
    )

    assert imports_imports_imports_collect_function_sources(module_text) is False


def test_imports_imports_imports_collect_function_sources_supports_aliased_import():
    module_text = (
        "from tests.ast_import_utils import imports_imports_collect_function_sources as helper\n"
        "helper('dummy')\n"
    )

    assert imports_imports_imports_collect_function_sources(module_text) is True


def test_imports_imports_imports_collect_function_sources_ignores_non_from_imports():
    module_text = (
        "import tests.ast_import_utils as import_utils\n"
        "import_utils.imports_imports_collect_function_sources('dummy')\n"
    )

    assert imports_imports_imports_collect_function_sources(module_text) is False


def test_calls_symbol_detects_direct_function_call():
    module_text = (
        "from tests.ast_function_source_utils import collect_function_sources\n"
        "collect_function_sources('tests/test_job_request_wrapper_internal_reuse.py')\n"
    )

    assert calls_symbol(module_text, "collect_function_sources") is True


def test_calls_symbol_detects_attribute_function_call():
    module_text = (
        "import tests.ast_import_utils as import_utils\n"
        "import_utils.imports_collect_function_sources('dummy')\n"
    )

    assert calls_symbol(module_text, "imports_collect_function_sources") is True


def test_calls_symbol_ignores_non_call_symbol_usage():
    module_text = (
        "imports_collect_function_sources = 'not a function call'\n"
        "print(imports_collect_function_sources)\n"
    )

    assert calls_symbol(module_text, "imports_collect_function_sources") is False
