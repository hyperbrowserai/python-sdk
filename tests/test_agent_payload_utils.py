from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.agent_payload_utils import build_agent_start_payload
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.agents.cua import StartCuaTaskParams


def test_build_agent_start_payload_serializes_model():
    payload = build_agent_start_payload(
        StartCuaTaskParams(task="open docs"),
        error_message="serialize failed",
    )

    assert payload == {"task": "open docs"}


def test_build_agent_start_payload_wraps_runtime_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartCuaTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(StartCuaTaskParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(HyperbrowserError, match="serialize failed") as exc_info:
        build_agent_start_payload(
            params,
            error_message="serialize failed",
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_agent_start_payload_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartCuaTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(StartCuaTaskParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        build_agent_start_payload(
            params,
            error_message="serialize failed",
        )

    assert exc_info.value.original_error is None


def test_build_agent_start_payload_rejects_non_dict_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartCuaTaskParams(task="open docs")

    monkeypatch.setattr(
        StartCuaTaskParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"task": "open docs"}),
    )

    with pytest.raises(HyperbrowserError, match="serialize failed") as exc_info:
        build_agent_start_payload(
            params,
            error_message="serialize failed",
        )

    assert exc_info.value.original_error is None
