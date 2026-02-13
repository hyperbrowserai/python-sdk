from collections.abc import Mapping
from typing import cast

import pytest
from pydantic import BaseModel

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.base import APIResponse


class _SampleResponseModel(BaseModel):
    name: str
    retries: int = 0


class _RaisesHyperbrowserModel:
    def __init__(self, **kwargs):
        _ = kwargs
        raise HyperbrowserError("model validation failed")


class _BrokenKeysMapping(Mapping[str, object]):
    def __iter__(self):
        raise RuntimeError("cannot iterate mapping keys")

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        _ = key
        return "value"


def test_api_response_from_json_parses_model_data() -> None:
    response = APIResponse.from_json(
        {"name": "job-1", "retries": 2}, _SampleResponseModel
    )

    assert isinstance(response.data, _SampleResponseModel)
    assert response.status_code == 200
    assert response.data.name == "job-1"
    assert response.data.retries == 2


def test_api_response_from_json_rejects_non_mapping_inputs() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to parse response data for _SampleResponseModel: "
            "expected a mapping but received list"
        ),
    ):
        APIResponse.from_json(
            cast("dict[str, object]", ["not-a-mapping"]),
            _SampleResponseModel,
        )


def test_api_response_from_json_rejects_non_string_mapping_keys() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to parse response data for _SampleResponseModel: "
            "expected string keys but received int"
        ),
    ):
        APIResponse.from_json(
            cast("dict[str, object]", {1: "job-1"}),
            _SampleResponseModel,
        )


def test_api_response_from_json_wraps_non_hyperbrowser_errors() -> None:
    with pytest.raises(
        HyperbrowserError,
        match="Failed to parse response data for _SampleResponseModel",
    ) as exc_info:
        APIResponse.from_json({"retries": 1}, _SampleResponseModel)

    assert exc_info.value.original_error is not None


def test_api_response_from_json_wraps_unreadable_mapping_keys() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to parse response data for _SampleResponseModel: "
            "unable to read mapping keys"
        ),
    ) as exc_info:
        APIResponse.from_json(_BrokenKeysMapping(), _SampleResponseModel)

    assert exc_info.value.original_error is not None


def test_api_response_from_json_preserves_hyperbrowser_errors() -> None:
    with pytest.raises(HyperbrowserError, match="model validation failed") as exc_info:
        APIResponse.from_json({}, _RaisesHyperbrowserModel)

    assert exc_info.value.original_error is None
