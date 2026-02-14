import io
from os import PathLike
from pathlib import Path

import pytest

from hyperbrowser.client.managers.session_upload_utils import (
    normalize_upload_file_input,
)
from hyperbrowser.exceptions import HyperbrowserError


def test_normalize_upload_file_input_returns_path_for_plain_string(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    normalized_path, file_obj = normalize_upload_file_input(str(file_path))

    assert normalized_path == str(file_path)
    assert file_obj is None


def test_normalize_upload_file_input_returns_path_for_pathlike(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    normalized_path, file_obj = normalize_upload_file_input(file_path)

    assert normalized_path == str(file_path)
    assert file_obj is None


def test_normalize_upload_file_input_rejects_string_subclass():
    class _PathString(str):
        pass

    with pytest.raises(
        HyperbrowserError, match="file_input path must be a plain string path"
    ) as exc_info:
        normalize_upload_file_input(_PathString("/tmp/file.txt"))  # type: ignore[arg-type]

    assert exc_info.value.original_error is None


def test_normalize_upload_file_input_wraps_invalid_pathlike_state_errors():
    class _BrokenPathLike(PathLike[str]):
        def __fspath__(self) -> str:
            raise RuntimeError("broken fspath")

    with pytest.raises(
        HyperbrowserError, match="file_input path is invalid"
    ) as exc_info:
        normalize_upload_file_input(_BrokenPathLike())

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_normalize_upload_file_input_uses_fspath_path_in_missing_file_errors():
    class _StringifyFailingPathLike(PathLike[str]):
        def __fspath__(self) -> str:
            return "/tmp/nonexistent-path-for-upload-utils-test"

        def __str__(self) -> str:
            raise RuntimeError("broken stringify")

    with pytest.raises(HyperbrowserError, match="Upload file not found at path: /tmp/nonexistent-path-for-upload-utils-test") as exc_info:
        normalize_upload_file_input(_StringifyFailingPathLike())

    assert exc_info.value.original_error is None


def test_normalize_upload_file_input_returns_open_file_like_object():
    file_obj = io.BytesIO(b"content")

    normalized_path, normalized_file_obj = normalize_upload_file_input(file_obj)

    assert normalized_path is None
    assert normalized_file_obj is file_obj


def test_normalize_upload_file_input_rejects_closed_file_like_object():
    file_obj = io.BytesIO(b"content")
    file_obj.close()

    with pytest.raises(HyperbrowserError, match="file-like object must be open"):
        normalize_upload_file_input(file_obj)


def test_normalize_upload_file_input_rejects_non_callable_read_attribute():
    fake_file = type("FakeFile", (), {"read": "not-callable"})()

    with pytest.raises(HyperbrowserError, match="file_input must be a file path"):
        normalize_upload_file_input(fake_file)  # type: ignore[arg-type]
