from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.serialization_utils import (
    serialize_model_dump_or_default,
    serialize_model_dump_to_dict,
    serialize_optional_model_dump_to_dict,
)
from hyperbrowser.exceptions import HyperbrowserError


class _ModelWithPayload:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def model_dump(self, *, exclude_none, by_alias):
        self.calls.append((exclude_none, by_alias))
        return self.payload


class _ModelWithRuntimeError:
    def model_dump(self, *, exclude_none, by_alias):
        _ = exclude_none
        _ = by_alias
        raise RuntimeError("broken model_dump")


class _ModelWithHyperbrowserError:
    def model_dump(self, *, exclude_none, by_alias):
        _ = exclude_none
        _ = by_alias
        raise HyperbrowserError("custom failure")


def test_serialize_model_dump_to_dict_returns_payload_and_forwards_flags():
    model = _ModelWithPayload({"value": 1})

    payload = serialize_model_dump_to_dict(
        model,
        error_message="serialize failure",
        exclude_none=False,
        by_alias=False,
    )

    assert payload == {"value": 1}
    assert model.calls == [(False, False)]


def test_serialize_model_dump_to_dict_wraps_runtime_errors():
    with pytest.raises(HyperbrowserError, match="serialize failure") as exc_info:
        serialize_model_dump_to_dict(
            _ModelWithRuntimeError(),
            error_message="serialize failure",
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_serialize_model_dump_to_dict_preserves_hyperbrowser_errors():
    with pytest.raises(HyperbrowserError, match="custom failure") as exc_info:
        serialize_model_dump_to_dict(
            _ModelWithHyperbrowserError(),
            error_message="serialize failure",
        )

    assert exc_info.value.original_error is None


def test_serialize_model_dump_to_dict_rejects_non_dict_payloads():
    with pytest.raises(HyperbrowserError, match="serialize failure") as exc_info:
        serialize_model_dump_to_dict(
            _ModelWithPayload(MappingProxyType({"value": 1})),
            error_message="serialize failure",
        )

    assert exc_info.value.original_error is None


def test_serialize_optional_model_dump_to_dict_returns_empty_dict_for_none():
    assert (
        serialize_optional_model_dump_to_dict(
            None,
            error_message="serialize failure",
        )
        == {}
    )


def test_serialize_optional_model_dump_to_dict_serializes_non_none_values():
    model = _ModelWithPayload({"value": 1})

    payload = serialize_optional_model_dump_to_dict(
        model,
        error_message="serialize failure",
        exclude_none=False,
        by_alias=False,
    )

    assert payload == {"value": 1}
    assert model.calls == [(False, False)]


def test_serialize_model_dump_or_default_uses_default_factory_when_none():
    model = _ModelWithPayload({"value": 2})

    payload = serialize_model_dump_or_default(
        None,
        default_factory=lambda: model,
        error_message="serialize failure",
    )

    assert payload == {"value": 2}
    assert model.calls == [(True, True)]


def test_serialize_model_dump_or_default_uses_provided_model_when_present():
    default_model = _ModelWithPayload({"unused": True})
    provided_model = _ModelWithPayload({"value": 3})
    default_factory_called = False

    def _default_factory():
        nonlocal default_factory_called
        default_factory_called = True
        return default_model

    payload = serialize_model_dump_or_default(
        provided_model,
        default_factory=_default_factory,
        error_message="serialize failure",
        exclude_none=False,
        by_alias=False,
    )

    assert payload == {"value": 3}
    assert provided_model.calls == [(False, False)]
    assert default_model.calls == []
    assert default_factory_called is False


def test_serialize_model_dump_or_default_wraps_default_factory_errors():
    def _broken_default_factory():
        raise RuntimeError("default factory failed")

    with pytest.raises(HyperbrowserError, match="serialize failure") as exc_info:
        serialize_model_dump_or_default(
            None,
            default_factory=_broken_default_factory,
            error_message="serialize failure",
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_serialize_model_dump_or_default_preserves_hyperbrowser_default_factory_errors():
    def _broken_default_factory():
        raise HyperbrowserError("custom default failure")

    with pytest.raises(HyperbrowserError, match="custom default failure") as exc_info:
        serialize_model_dump_or_default(
            None,
            default_factory=_broken_default_factory,
            error_message="serialize failure",
        )

    assert exc_info.value.original_error is None
