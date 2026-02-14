from typing import Any, Type


def is_plain_instance(value: Any, expected_type: Type[object]) -> bool:
    return type(value) is expected_type


def is_subclass_instance(value: Any, expected_type: Type[object]) -> bool:
    value_type = type(value)
    return value_type is not expected_type and expected_type in value_type.__mro__


def is_plain_string(value: Any) -> bool:
    return is_plain_instance(value, str)


def is_string_subclass_instance(value: Any) -> bool:
    return is_subclass_instance(value, str)


def is_plain_int(value: Any) -> bool:
    return is_plain_instance(value, int)


def is_int_subclass_instance(value: Any) -> bool:
    return is_subclass_instance(value, int)
