import ast

import pytest

from tests.guardrail_ast_utils import (
    collect_attribute_call_lines,
    collect_list_keys_call_lines,
    collect_name_call_lines,
    collect_while_true_lines,
)

pytestmark = pytest.mark.architecture


SAMPLE_MODULE = ast.parse(
    """
values = list(mapping.keys())
result = helper()
other = obj.method()
while True:
    break
"""
)


def test_collect_name_call_lines_returns_named_calls():
    assert collect_name_call_lines(SAMPLE_MODULE, "helper") == [3]


def test_collect_attribute_call_lines_returns_attribute_calls():
    assert collect_attribute_call_lines(SAMPLE_MODULE, "method") == [4]


def test_collect_list_keys_call_lines_returns_list_key_calls():
    assert collect_list_keys_call_lines(SAMPLE_MODULE) == [2]


def test_collect_while_true_lines_returns_while_true_statements():
    assert collect_while_true_lines(SAMPLE_MODULE) == [5]
