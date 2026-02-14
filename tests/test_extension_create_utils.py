from pathlib import Path
from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.extension_create_utils import (
    normalize_extension_create_input,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams


def _create_test_extension_zip(tmp_path: Path) -> Path:
    file_path = tmp_path / "extension.zip"
    file_path.write_bytes(b"extension-bytes")
    return file_path


def test_normalize_extension_create_input_returns_file_path_and_payload(tmp_path):
    file_path = _create_test_extension_zip(tmp_path)
    params = CreateExtensionParams(name="my-extension", file_path=file_path)

    normalized_path, payload = normalize_extension_create_input(params)

    assert normalized_path == str(file_path.resolve())
    assert payload == {"name": "my-extension"}


def test_normalize_extension_create_input_rejects_invalid_param_type():
    with pytest.raises(HyperbrowserError, match="params must be CreateExtensionParams"):
        normalize_extension_create_input({"name": "bad"})  # type: ignore[arg-type]


def test_normalize_extension_create_input_rejects_subclass_param_type(tmp_path):
    class _Params(CreateExtensionParams):
        pass

    params = _Params(name="bad", file_path=_create_test_extension_zip(tmp_path))

    with pytest.raises(HyperbrowserError, match="params must be CreateExtensionParams"):
        normalize_extension_create_input(params)


def test_normalize_extension_create_input_wraps_serialization_errors(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(CreateExtensionParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extension create params"
    ) as exc_info:
        normalize_extension_create_input(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_normalize_extension_create_input_preserves_hyperbrowser_serialization_errors(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(CreateExtensionParams, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        normalize_extension_create_input(params)

    assert exc_info.value.original_error is None


def test_normalize_extension_create_input_rejects_non_dict_serialized_payload(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    params = CreateExtensionParams(
        name="serialize-extension",
        file_path=_create_test_extension_zip(tmp_path),
    )

    monkeypatch.setattr(
        CreateExtensionParams,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"name": "my-extension"}),
    )

    with pytest.raises(
        HyperbrowserError, match="Failed to serialize extension create params"
    ) as exc_info:
        normalize_extension_create_input(params)

    assert exc_info.value.original_error is None


def test_normalize_extension_create_input_rejects_missing_file(tmp_path):
    missing_path = tmp_path / "missing-extension.zip"
    params = CreateExtensionParams(name="missing-extension", file_path=missing_path)

    with pytest.raises(HyperbrowserError, match="Extension file not found"):
        normalize_extension_create_input(params)
