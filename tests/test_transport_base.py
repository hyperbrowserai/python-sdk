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


class _BrokenValueMapping(Mapping[str, object]):
    def __iter__(self):
        return iter(["name"])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        if key == "name":
            raise RuntimeError("cannot read value")
        raise KeyError(key)


class _BrokenNameMeta(type):
    def __getattribute__(cls, name: str):
        if name == "__name__":
            raise RuntimeError("cannot read model name")
        return super().__getattribute__(name)


class _BrokenNameModel(metaclass=_BrokenNameMeta):
    def __init__(self, **kwargs):
        self.name = kwargs["name"]
        self.retries = kwargs.get("retries", 0)


class _BlankNameCallableModel:
    __name__ = "   "

    def __call__(self, **kwargs):
        _ = kwargs
        raise RuntimeError("call failed")


class _LongControlNameCallableModel:
    __name__ = "  Model\t" + ("x" * 200)

    def __call__(self, **kwargs):
        _ = kwargs
        raise RuntimeError("call failed")


class _BrokenBlankKeyValueMapping(Mapping[str, object]):
    def __iter__(self):
        return iter(["   "])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        if key == "   ":
            raise RuntimeError("cannot read blank key value")
        raise KeyError(key)


class _BrokenLongKeyValueMapping(Mapping[str, object]):
    _KEY = "bad\t" + ("k" * 200)

    def __iter__(self):
        return iter([self._KEY])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        if key == self._KEY:
            raise RuntimeError("cannot read long key value")
        raise KeyError(key)


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


def test_api_response_from_json_parses_model_when_name_lookup_fails() -> None:
    response = APIResponse.from_json({"name": "job-1"}, _BrokenNameModel)

    assert isinstance(response.data, _BrokenNameModel)
    assert response.data.name == "job-1"
    assert response.status_code == 200


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


def test_api_response_from_json_wraps_unreadable_mapping_values() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to parse response data for _SampleResponseModel: "
            "unable to read value for key 'name'"
        ),
    ) as exc_info:
        APIResponse.from_json(_BrokenValueMapping(), _SampleResponseModel)

    assert exc_info.value.original_error is not None


def test_api_response_from_json_uses_default_name_for_blank_model_name() -> None:
    with pytest.raises(
        HyperbrowserError,
        match="Failed to parse response data for response model",
    ):
        APIResponse.from_json(
            {"name": "job-1"},
            cast("type[_SampleResponseModel]", _BlankNameCallableModel()),
        )


def test_api_response_from_json_sanitizes_and_truncates_model_name_in_errors() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=r"Failed to parse response data for Model\?x+\.\.\. \(truncated\)",
    ):
        APIResponse.from_json(
            {"name": "job-1"},
            cast("type[_SampleResponseModel]", _LongControlNameCallableModel()),
        )


def test_api_response_from_json_uses_placeholder_for_blank_mapping_key_in_errors() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to parse response data for _SampleResponseModel: "
            "unable to read value for key '<blank key>'"
        ),
    ):
        APIResponse.from_json(_BrokenBlankKeyValueMapping(), _SampleResponseModel)


def test_api_response_from_json_sanitizes_and_truncates_mapping_keys_in_errors() -> None:
    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to parse response data for _SampleResponseModel: "
            r"unable to read value for key 'bad\?k+\.\.\. \(truncated\)'"
        ),
    ):
        APIResponse.from_json(_BrokenLongKeyValueMapping(), _SampleResponseModel)


def test_api_response_from_json_preserves_hyperbrowser_errors() -> None:
    with pytest.raises(HyperbrowserError, match="model validation failed") as exc_info:
        APIResponse.from_json({}, _RaisesHyperbrowserModel)

    assert exc_info.value.original_error is None


def test_api_response_constructor_rejects_non_integer_status_code() -> None:
    with pytest.raises(HyperbrowserError, match="status_code must be an integer"):
        APIResponse(status_code="200")  # type: ignore[arg-type]


def test_api_response_constructor_rejects_boolean_status_code() -> None:
    with pytest.raises(HyperbrowserError, match="status_code must be an integer"):
        APIResponse(status_code=True)


@pytest.mark.parametrize("status_code", [99, 600])
def test_api_response_constructor_rejects_out_of_range_status_code(
    status_code: int,
) -> None:
    with pytest.raises(HyperbrowserError, match="status_code must be between 100 and 599"):
        APIResponse(status_code=status_code)


def test_api_response_from_status_rejects_boolean_status_code() -> None:
    with pytest.raises(HyperbrowserError, match="status_code must be an integer"):
        APIResponse.from_status(True)  # type: ignore[arg-type]


@pytest.mark.parametrize("status_code", [99, 600])
def test_api_response_from_status_rejects_out_of_range_status_code(
    status_code: int,
) -> None:
    with pytest.raises(HyperbrowserError, match="status_code must be between 100 and 599"):
        APIResponse.from_status(status_code)
