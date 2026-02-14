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


def test_ensure_existing_file_path_rejects_non_string_missing_message(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="missing_file_message must be a string"
    ):
        ensure_existing_file_path(
            str(file_path),
            missing_file_message=123,  # type: ignore[arg-type]
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_blank_missing_message(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="missing_file_message must not be empty"
    ):
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="   ",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_control_chars_in_missing_message(
    tmp_path: Path,
):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError,
        match="missing_file_message must not contain control characters",
    ):
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing\tmessage",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_non_string_not_file_message(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(HyperbrowserError, match="not_file_message must be a string"):
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message=123,  # type: ignore[arg-type]
        )


def test_ensure_existing_file_path_rejects_blank_not_file_message(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(HyperbrowserError, match="not_file_message must not be empty"):
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message="  ",
        )


def test_ensure_existing_file_path_rejects_control_chars_in_not_file_message(
    tmp_path: Path,
):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError,
        match="not_file_message must not contain control characters",
    ):
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message="not-file\nmessage",
        )


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
    with pytest.raises(HyperbrowserError, match="file_path must not be empty"):
        ensure_existing_file_path(
            "   ",
            missing_file_message="missing",
            not_file_message="not-file",
        )


def test_ensure_existing_file_path_rejects_surrounding_whitespace():
    with pytest.raises(
        HyperbrowserError,
        match="file_path must not contain leading or trailing whitespace",
    ):
        ensure_existing_file_path(
            " /tmp/file.txt",
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


def test_ensure_existing_file_path_rejects_control_character_paths():
    with pytest.raises(
        HyperbrowserError, match="file_path must not contain control characters"
    ):
        ensure_existing_file_path(
            "bad\tpath.txt",
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


def test_ensure_existing_file_path_wraps_unexpected_exists_errors(monkeypatch):
    def raising_exists(path: str) -> bool:
        _ = path
        raise RuntimeError("unexpected exists failure")

    monkeypatch.setattr(file_utils.os.path, "exists", raising_exists)

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            "/tmp/maybe-invalid",
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is not None


def test_ensure_existing_file_path_wraps_unexpected_isfile_errors(
    monkeypatch, tmp_path: Path
):
    file_path = tmp_path / "target.txt"
    file_path.write_text("content")

    def raising_isfile(path: str) -> bool:
        _ = path
        raise RuntimeError("unexpected isfile failure")

    monkeypatch.setattr(file_utils.os.path, "isfile", raising_isfile)

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is not None


def test_ensure_existing_file_path_wraps_non_boolean_exists_results(monkeypatch):
    class _BrokenTruthValue:
        def __bool__(self) -> bool:
            raise RuntimeError("cannot coerce exists result")

    def invalid_exists(path: str):
        _ = path
        return _BrokenTruthValue()

    monkeypatch.setattr(file_utils.os.path, "exists", invalid_exists)

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            "/tmp/maybe-invalid",
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is not None


def test_ensure_existing_file_path_wraps_non_boolean_isfile_results(
    monkeypatch, tmp_path: Path
):
    class _BrokenTruthValue:
        def __bool__(self) -> bool:
            raise RuntimeError("cannot coerce isfile result")

    file_path = tmp_path / "target.txt"
    file_path.write_text("content")

    def invalid_isfile(path: str):
        _ = path
        return _BrokenTruthValue()

    monkeypatch.setattr(file_utils.os.path, "isfile", invalid_isfile)

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is not None


def test_ensure_existing_file_path_wraps_fspath_runtime_errors():
    class _BrokenPathLike:
        def __fspath__(self) -> str:
            raise RuntimeError("bad fspath")

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            _BrokenPathLike(),  # type: ignore[arg-type]
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is not None


def test_ensure_existing_file_path_preserves_hyperbrowser_fspath_errors():
    class _BrokenPathLike:
        def __fspath__(self) -> str:
            raise HyperbrowserError("custom fspath failure")

    with pytest.raises(HyperbrowserError, match="custom fspath failure") as exc_info:
        ensure_existing_file_path(
            _BrokenPathLike(),  # type: ignore[arg-type]
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


def test_ensure_existing_file_path_wraps_missing_message_strip_runtime_errors(
    tmp_path: Path,
):
    class _BrokenMissingMessage(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("missing message strip exploded")

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize missing_file_message"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message=_BrokenMissingMessage("missing"),
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_ensure_existing_file_path_wraps_missing_message_string_subclass_strip_results(
    tmp_path: Path,
):
    class _BrokenMissingMessage(str):
        class _NormalizedMessage(str):
            pass

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedMessage("missing")

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize missing_file_message"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message=_BrokenMissingMessage("missing"),
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, TypeError)


def test_ensure_existing_file_path_wraps_missing_message_character_validation_failures(
    tmp_path: Path,
):
    class _BrokenMissingMessage(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return "missing"

        def __iter__(self):
            raise RuntimeError("missing message iteration exploded")

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="Failed to validate missing_file_message characters"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message=_BrokenMissingMessage("missing"),
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_ensure_existing_file_path_preserves_hyperbrowser_missing_message_strip_errors(
    tmp_path: Path,
):
    class _BrokenMissingMessage(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom missing message strip failure")

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="custom missing message strip failure"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message=_BrokenMissingMessage("missing"),
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


def test_ensure_existing_file_path_wraps_not_file_message_strip_runtime_errors(
    tmp_path: Path,
):
    class _BrokenNotFileMessage(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("not-file message strip exploded")

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize not_file_message"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message=_BrokenNotFileMessage("not-file"),
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_ensure_existing_file_path_wraps_not_file_message_string_subclass_strip_results(
    tmp_path: Path,
):
    class _BrokenNotFileMessage(str):
        class _NormalizedMessage(str):
            pass

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedMessage("not-file")

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize not_file_message"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message=_BrokenNotFileMessage("not-file"),
        )

    assert isinstance(exc_info.value.original_error, TypeError)


def test_ensure_existing_file_path_wraps_file_path_strip_runtime_errors():
    class _BrokenPath(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("path strip exploded")

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_ensure_existing_file_path_wraps_file_path_string_subclass_strip_results():
    class _BrokenPath(str):
        class _NormalizedPath(str):
            pass

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedPath("/tmp/path.txt")

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, TypeError)


def test_ensure_existing_file_path_wraps_file_path_contains_runtime_errors():
    class _BrokenPath(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __contains__(self, item):  # type: ignore[override]
            _ = item
            raise RuntimeError("path contains exploded")

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, TypeError)


def test_ensure_existing_file_path_wraps_file_path_character_iteration_runtime_errors():
    class _BrokenPath(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __contains__(self, item):  # type: ignore[override]
            _ = item
            return False

        def __iter__(self):
            raise RuntimeError("path iteration exploded")

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert isinstance(exc_info.value.original_error, TypeError)
