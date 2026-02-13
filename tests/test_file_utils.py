from pathlib import Path

import pytest

import hyperbrowser.client.file_utils as file_utils
from hyperbrowser.client.file_utils import ensure_existing_file_path
from hyperbrowser.exceptions import HyperbrowserError


def test_ensure_existing_file_path_accepts_existing_file(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    normalized_path = ensure_existing_file_path(
        str(file_path),
        missing_file_message="missing",
        not_file_message="not-file",
    )

    assert normalized_path == str(file_path)


def test_ensure_existing_file_path_accepts_pathlike_inputs(tmp_path: Path):
    file_path = tmp_path / "pathlike-file.txt"
    file_path.write_text("content")

    normalized_path = ensure_existing_file_path(
        file_path,
        missing_file_message="missing",
        not_file_message="not-file",
    )

    assert normalized_path == str(file_path)


def test_ensure_existing_file_path_raises_for_missing_file(tmp_path: Path):
    missing_path = tmp_path / "missing.txt"

    with pytest.raises(HyperbrowserError, match="missing"):
        ensure_existing_file_path(
            str(missing_path),
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_raises_for_directory(tmp_path: Path):
    with pytest.raises(HyperbrowserError, match="not-file"):
        ensure_existing_file_path(
            str(tmp_path),
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_invalid_path_type():
    with pytest.raises(
        HyperbrowserError, match="file_path must be a string or os.PathLike object"
    ):
        ensure_existing_file_path(
            123,  # type: ignore[arg-type]
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_non_string_fspath_results():
    with pytest.raises(HyperbrowserError, match="file_path must resolve to a string"):
        ensure_existing_file_path(
            b"/tmp/bytes-path",  # type: ignore[arg-type]
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_empty_string_paths():
    with pytest.raises(HyperbrowserError, match="file_path must not be empty"):
        ensure_existing_file_path(
            "",
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_null_byte_paths():
    with pytest.raises(
        HyperbrowserError, match="file_path must not contain null bytes"
    ):
        ensure_existing_file_path(
            "bad\x00path.txt",
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_wraps_invalid_path_os_errors(monkeypatch):
    def raising_exists(path: str) -> bool:
        raise OSError("invalid path")

    monkeypatch.setattr(file_utils.os.path, "exists", raising_exists)

    with pytest.raises(HyperbrowserError, match="file_path is invalid"):
        ensure_existing_file_path(
            "/tmp/maybe-invalid",
            missing_file_message="missing",
            not_file_message="not-file",
        )
