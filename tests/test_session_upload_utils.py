import io
from os import PathLike
from pathlib import Path

import pytest

import hyperbrowser.client.managers.session_upload_utils as session_upload_utils
from hyperbrowser.client.managers.session_upload_utils import (
    open_upload_files_from_input,
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


def test_normalize_upload_file_input_survives_string_subclass_fspath_in_error_messages():
    class _PathString(str):
        def __str__(self) -> str:  # type: ignore[override]
            raise RuntimeError("broken stringify")

    class _PathLike(PathLike[str]):
        def __fspath__(self) -> str:
            return _PathString("/tmp/nonexistent-subclass-path-for-upload-utils-test")

    with pytest.raises(
        HyperbrowserError,
        match="file_path must resolve to a string path",
    ) as exc_info:
        normalize_upload_file_input(_PathLike())

    assert exc_info.value.original_error is None


def test_normalize_upload_file_input_rejects_control_character_paths_before_message_validation():
    with pytest.raises(
        HyperbrowserError,
        match="file_path must not contain control characters",
    ) as exc_info:
        normalize_upload_file_input("bad\tpath.txt")

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


def test_normalize_upload_file_input_wraps_file_like_read_state_errors():
    class _BrokenFileLike:
        @property
        def read(self):
            raise RuntimeError("broken read")

    with pytest.raises(
        HyperbrowserError, match="file_input file-like object state is invalid"
    ) as exc_info:
        normalize_upload_file_input(_BrokenFileLike())  # type: ignore[arg-type]

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_normalize_upload_file_input_preserves_hyperbrowser_read_state_errors():
    class _BrokenFileLike:
        @property
        def read(self):
            raise HyperbrowserError("custom read state error")

    with pytest.raises(HyperbrowserError, match="custom read state error") as exc_info:
        normalize_upload_file_input(_BrokenFileLike())  # type: ignore[arg-type]

    assert exc_info.value.original_error is None


def test_normalize_upload_file_input_preserves_hyperbrowser_closed_state_errors():
    class _BrokenFileLike:
        def read(self):
            return b"content"

        @property
        def closed(self):
            raise HyperbrowserError("custom closed-state error")

    with pytest.raises(
        HyperbrowserError, match="custom closed-state error"
    ) as exc_info:
        normalize_upload_file_input(_BrokenFileLike())  # type: ignore[arg-type]

    assert exc_info.value.original_error is None


def test_open_upload_files_from_input_opens_and_closes_path_input(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with open_upload_files_from_input(str(file_path)) as files:
        assert "file" in files
        assert files["file"].closed is False
        assert files["file"].read() == b"content"

    assert files["file"].closed is True


def test_open_upload_files_from_input_reuses_file_like_object():
    file_obj = io.BytesIO(b"content")

    with open_upload_files_from_input(file_obj) as files:
        assert files == {"file": file_obj}


def test_open_upload_files_from_input_rejects_missing_normalized_file_object(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        session_upload_utils,
        "normalize_upload_file_input",
        lambda file_input: (None, None),
    )

    with pytest.raises(
        HyperbrowserError, match="file_input must be a file path or file-like object"
    ):
        with open_upload_files_from_input(io.BytesIO(b"content")):
            pass
