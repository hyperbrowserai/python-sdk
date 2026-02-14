from types import MappingProxyType

import pytest
from pydantic import BaseModel

import hyperbrowser.client.managers.extract_payload_utils as extract_payload_utils
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extract import StartExtractJobParams


def test_build_extract_start_payload_requires_schema_or_prompt():
    params = StartExtractJobParams(urls=["https://example.com"])

    with pytest.raises(HyperbrowserError, match="Either schema or prompt must be provided"):
        extract_payload_utils.build_extract_start_payload(params)


def test_build_extract_start_payload_serializes_prompt_payload():
    params = StartExtractJobParams(
        urls=["https://example.com"],
        prompt="extract content",
    )

    payload = extract_payload_utils.build_extract_start_payload(params)

    assert payload["urls"] == ["https://example.com"]
    assert payload["prompt"] == "extract content"


def test_build_extract_start_payload_resolves_schema_values(monkeypatch: pytest.MonkeyPatch):
    class _SchemaModel(BaseModel):
        title: str

    params = StartExtractJobParams(
        urls=["https://example.com"],
        schema=_SchemaModel,
    )

    monkeypatch.setattr(
        extract_payload_utils,
        "resolve_schema_input",
        lambda schema_input: {"resolvedSchema": schema_input.__name__},
    )

    payload = extract_payload_utils.build_extract_start_payload(params)

    assert payload["schema"] == {"resolvedSchema": "_SchemaModel"}


def test_build_extract_start_payload_wraps_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartExtractJobParams(
        urls=["https://example.com"],
        prompt="extract content",
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(StartExtractJobParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extract start params"
    ) as exc_info:
        extract_payload_utils.build_extract_start_payload(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_build_extract_start_payload_preserves_hyperbrowser_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartExtractJobParams(
        urls=["https://example.com"],
        prompt="extract content",
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(StartExtractJobParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        extract_payload_utils.build_extract_start_payload(params)

    assert exc_info.value.original_error is None


def test_build_extract_start_payload_rejects_non_dict_serialized_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    params = StartExtractJobParams(
        urls=["https://example.com"],
        prompt="extract content",
    )

    monkeypatch.setattr(
        StartExtractJobParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"urls": ["https://example.com"]}),
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extract start params"
    ) as exc_info:
        extract_payload_utils.build_extract_start_payload(params)

    assert exc_info.value.original_error is None
