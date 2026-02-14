from types import MappingProxyType

import pytest
from pydantic import BaseModel
from typing import Optional

from hyperbrowser.client.managers.computer_action_payload_utils import (
    build_computer_action_payload,
)
from hyperbrowser.exceptions import HyperbrowserError


class _ActionParams(BaseModel):
    action_type: str
    return_screenshot: Optional[bool] = None


def test_build_computer_action_payload_serializes_pydantic_models():
    payload = build_computer_action_payload(
        _ActionParams(action_type="screenshot", return_screenshot=True)
    )

    assert payload == {"action_type": "screenshot", "return_screenshot": True}


def test_build_computer_action_payload_passes_through_non_models():
    raw_payload = {"foo": "bar"}

    assert build_computer_action_payload(raw_payload) is raw_payload


def test_build_computer_action_payload_wraps_runtime_model_dump_errors():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            raise RuntimeError("broken model_dump")

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize computer action params"
    ) as exc_info:
        build_computer_action_payload(_BrokenParams())

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_computer_action_payload_preserves_hyperbrowser_model_dump_errors():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            raise HyperbrowserError("custom model_dump failure")

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        build_computer_action_payload(_BrokenParams())

    assert exc_info.value.original_error is None


def test_build_computer_action_payload_rejects_non_dict_model_dump_results():
    class _BrokenParams(BaseModel):
        def model_dump(self, *args, **kwargs):  # type: ignore[override]
            _ = args
            _ = kwargs
            return MappingProxyType({"actionType": "screenshot"})

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize computer action params"
    ) as exc_info:
        build_computer_action_payload(_BrokenParams())

    assert exc_info.value.original_error is None
