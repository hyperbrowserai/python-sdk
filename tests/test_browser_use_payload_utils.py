from types import MappingProxyType

import pytest
from pydantic import BaseModel

import hyperbrowser.client.managers.browser_use_payload_utils as browser_use_payload_utils
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams


def test_build_browser_use_start_payload_serializes_params():
    params = StartBrowserUseTaskParams(task="open docs")

    payload = browser_use_payload_utils.build_browser_use_start_payload(params)

    assert payload == {"task": "open docs"}


def test_build_browser_use_start_payload_includes_resolved_output_schema(
    monkeypatch: pytest.MonkeyPatch,
):
    class _SchemaModel(BaseModel):
        value: str

    params = StartBrowserUseTaskParams(
        task="open docs",
        output_model_schema=_SchemaModel,
    )

    monkeypatch.setattr(
        browser_use_payload_utils,
        "resolve_schema_input",
        lambda schema_input: {"resolvedSchema": schema_input.__name__},
    )

    payload = browser_use_payload_utils.build_browser_use_start_payload(params)

    assert payload["outputModelSchema"] == {"resolvedSchema": "_SchemaModel"}


def test_build_browser_use_start_payload_wraps_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartBrowserUseTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(
        StartBrowserUseTaskParams,
        "model_dump",
        _raise_model_dump_error,
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize browser-use start params"
    ) as exc_info:
        browser_use_payload_utils.build_browser_use_start_payload(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_browser_use_start_payload_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartBrowserUseTaskParams(task="open docs")

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(
        StartBrowserUseTaskParams,
        "model_dump",
        _raise_model_dump_error,
    )

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        browser_use_payload_utils.build_browser_use_start_payload(params)

    assert exc_info.value.original_error is None


def test_build_browser_use_start_payload_rejects_non_dict_serialized_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartBrowserUseTaskParams(task="open docs")

    monkeypatch.setattr(
        StartBrowserUseTaskParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"task": "open docs"}),
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize browser-use start params"
    ) as exc_info:
        browser_use_payload_utils.build_browser_use_start_payload(params)

    assert exc_info.value.original_error is None
