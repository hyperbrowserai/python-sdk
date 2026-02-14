from pathlib import Path

from tests.guardrail_ast_utils import (
    collect_attribute_call_lines,
    collect_name_call_lines,
    read_module_ast,
)

TOOLS_MODULE = Path("hyperbrowser/tools/__init__.py")

def test_tools_module_uses_shared_mapping_read_helpers():
    module = read_module_ast(TOOLS_MODULE)

    keys_calls = collect_attribute_call_lines(module, "keys")
    read_key_calls = collect_name_call_lines(module, "read_string_mapping_keys")
    copy_value_calls = collect_name_call_lines(
        module, "copy_mapping_values_by_string_keys"
    )

    assert keys_calls == []
    assert read_key_calls != []
    assert copy_value_calls != []
