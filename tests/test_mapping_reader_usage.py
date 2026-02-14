from pathlib import Path

import pytest

from tests.guardrail_ast_utils import (
    collect_list_keys_call_lines,
    collect_name_call_lines,
    read_module_ast,
)

pytestmark = pytest.mark.architecture

_TARGET_FILES = (
    Path("hyperbrowser/client/managers/response_utils.py"),
    Path("hyperbrowser/transport/base.py"),
    Path("hyperbrowser/client/managers/list_parsing_utils.py"),
)


def test_core_mapping_parsers_use_shared_mapping_reader():
    violations: list[str] = []
    missing_reader_calls: list[str] = []

    for relative_path in _TARGET_FILES:
        module = read_module_ast(relative_path)
        list_keys_calls = collect_list_keys_call_lines(module)
        if list_keys_calls:
            for line in list_keys_calls:
                violations.append(f"{relative_path}:{line}")
        reader_calls = collect_name_call_lines(module, "read_string_key_mapping")
        if not reader_calls:
            missing_reader_calls.append(str(relative_path))

    assert violations == []
    assert missing_reader_calls == []
