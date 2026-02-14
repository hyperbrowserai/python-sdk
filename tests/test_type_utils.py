from hyperbrowser.type_utils import (
    is_int_subclass_instance,
    is_plain_instance,
    is_plain_int,
    is_plain_string,
    is_string_subclass_instance,
    is_subclass_instance,
)


def test_is_plain_instance_requires_concrete_type_match():
    assert is_plain_instance("value", str) is True
    assert is_plain_instance(10, int) is True
    assert is_plain_instance(True, int) is False
    assert is_plain_instance("value", int) is False


def test_is_subclass_instance_detects_string_subclasses_only():
    class _StringSubclass(str):
        pass

    assert is_subclass_instance(_StringSubclass("value"), str) is True
    assert is_subclass_instance("value", str) is False
    assert is_subclass_instance(10, str) is False


def test_string_helpers_enforce_plain_string_boundaries():
    class _StringSubclass(str):
        pass

    assert is_plain_string("value") is True
    assert is_plain_string(_StringSubclass("value")) is False
    assert is_string_subclass_instance("value") is False
    assert is_string_subclass_instance(_StringSubclass("value")) is True


def test_string_helpers_reject_non_string_inputs():
    assert is_plain_string(None) is False
    assert is_plain_string(123) is False
    assert is_plain_string(b"value") is False
    assert is_string_subclass_instance(None) is False
    assert is_string_subclass_instance(123) is False
    assert is_string_subclass_instance(b"value") is False


def test_int_helpers_enforce_plain_integer_boundaries():
    class _IntSubclass(int):
        pass

    assert is_plain_int(10) is True
    assert is_plain_int(_IntSubclass(10)) is False
    assert is_int_subclass_instance(10) is False
    assert is_int_subclass_instance(_IntSubclass(10)) is True
    assert is_int_subclass_instance(True) is True


def test_int_helpers_reject_non_integer_and_handle_indirect_subclasses():
    class _IntSubclass(int):
        pass

    class _NestedIntSubclass(_IntSubclass):
        pass

    assert is_plain_int(3.14) is False
    assert is_plain_int(False) is False
    assert is_plain_int(None) is False
    assert is_int_subclass_instance(3.14) is False
    assert is_int_subclass_instance(None) is False
    assert is_int_subclass_instance(_NestedIntSubclass(7)) is True
