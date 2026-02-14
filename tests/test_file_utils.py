from pathlib import Path

import pytest

import hyperbrowser.client.file_utils as file_utils
from hyperbrowser.client.file_utils import (
    build_file_path_error_message,
    build_open_file_error_message,
    ensure_existing_file_path,
    format_file_path_for_error,
    open_binary_file,
)
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


def test_ensure_existing_file_path_rejects_string_subclass_missing_message(
    tmp_path: Path,
):
    class _MissingMessage(str):
        pass

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="missing_file_message must be a string"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message=_MissingMessage("missing"),
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


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


def test_ensure_existing_file_path_rejects_string_subclass_not_file_message(
    tmp_path: Path,
):
    class _NotFileMessage(str):
        pass

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(
        HyperbrowserError, match="not_file_message must be a string"
    ) as exc_info:
        ensure_existing_file_path(
            str(file_path),
            missing_file_message="missing",
            not_file_message=_NotFileMessage("not-file"),
        )

    assert exc_info.value.original_error is None


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


def test_ensure_existing_file_path_rejects_string_subclass_fspath_results():
    class _PathLike:
        class _PathString(str):
            pass

        def __fspath__(self):
            return self._PathString("/tmp/subclass-path")

    with pytest.raises(HyperbrowserError, match="file_path must resolve to a string"):
        ensure_existing_file_path(
            _PathLike(),  # type: ignore[arg-type]
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


def test_format_file_path_for_error_sanitizes_control_characters():
    display_path = format_file_path_for_error("bad\tpath\nvalue")

    assert display_path == "bad?path?value"


def test_format_file_path_for_error_truncates_long_paths():
    display_path = format_file_path_for_error("abcdef", max_length=5)

    assert display_path == "ab..."


def test_format_file_path_for_error_uses_default_for_non_int_max_length():
    display_path = format_file_path_for_error("abcdef", max_length="3")  # type: ignore[arg-type]

    assert display_path == "abcdef"


def test_format_file_path_for_error_uses_default_for_non_positive_max_length():
    display_path = format_file_path_for_error("abcdef", max_length=0)
    assert display_path == "abcdef"
    display_path = format_file_path_for_error("abcdef", max_length=-10)
    assert display_path == "abcdef"


def test_format_file_path_for_error_uses_default_for_bool_max_length():
    display_path = format_file_path_for_error("abcdef", max_length=False)  # type: ignore[arg-type]

    assert display_path == "abcdef"


def test_format_file_path_for_error_falls_back_for_non_string_values():
    assert format_file_path_for_error(object()) == "<provided path>"


def test_format_file_path_for_error_falls_back_for_fspath_failures():
    class _BrokenPathLike:
        def __fspath__(self) -> str:
            raise RuntimeError("bad fspath")

    assert format_file_path_for_error(_BrokenPathLike()) == "<provided path>"


def test_format_file_path_for_error_uses_pathlike_string_values():
    class _PathLike:
        def __fspath__(self) -> str:
            return "/tmp/path-value"

    assert format_file_path_for_error(_PathLike()) == "/tmp/path-value"


def test_build_open_file_error_message_uses_prefix_and_sanitized_path():
    message = build_open_file_error_message(
        "bad\tpath.txt",
        prefix="Failed to open upload file at path",
    )

    assert message == "Failed to open upload file at path: bad?path.txt"


def test_build_file_path_error_message_uses_prefix_and_sanitized_path():
    message = build_file_path_error_message(
        "bad\tpath.txt",
        prefix="Upload file not found at path",
        default_prefix="Upload file not found at path",
    )

    assert message == "Upload file not found at path: bad?path.txt"


def test_build_file_path_error_message_defaults_default_prefix_to_prefix():
    message = build_file_path_error_message(
        "bad\tpath.txt",
        prefix="Upload file not found at path",
    )

    assert message == "Upload file not found at path: bad?path.txt"


def test_build_file_path_error_message_uses_default_for_non_string_prefix():
    message = build_file_path_error_message(
        "/tmp/path.txt",
        prefix=123,  # type: ignore[arg-type]
        default_prefix="Upload file not found at path",
    )

    assert message == "Upload file not found at path: /tmp/path.txt"


def test_build_file_path_error_message_uses_open_default_when_default_prefix_invalid():
    message = build_file_path_error_message(
        "/tmp/path.txt",
        prefix=123,  # type: ignore[arg-type]
        default_prefix="   ",
    )

    assert message == "Failed to open file at path: /tmp/path.txt"


def test_build_file_path_error_message_sanitizes_default_prefix_when_prefix_invalid():
    message = build_file_path_error_message(
        "/tmp/path.txt",
        prefix=123,  # type: ignore[arg-type]
        default_prefix="Custom\tdefault",
    )

    assert message == "Custom?default: /tmp/path.txt"


def test_build_open_file_error_message_uses_default_prefix_for_non_string():
    message = build_open_file_error_message(
        "/tmp/path.txt",
        prefix=123,  # type: ignore[arg-type]
    )

    assert message == "Failed to open file at path: /tmp/path.txt"


def test_build_open_file_error_message_uses_default_prefix_for_blank_string():
    message = build_open_file_error_message(
        "/tmp/path.txt",
        prefix="   ",
    )

    assert message == "Failed to open file at path: /tmp/path.txt"


def test_build_open_file_error_message_sanitizes_control_chars_in_prefix():
    message = build_open_file_error_message(
        "/tmp/path.txt",
        prefix="Failed\topen",
    )

    assert message == "Failed?open: /tmp/path.txt"


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


def test_ensure_existing_file_path_rejects_string_subclass_path_inputs_before_strip():
    class _BrokenPath(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("path strip exploded")

    with pytest.raises(
        HyperbrowserError, match="file_path must resolve to a string path"
    ) as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


def test_ensure_existing_file_path_rejects_string_subclass_path_strip_result_inputs():
    class _BrokenPath(str):
        class _NormalizedPath(str):
            pass

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedPath("/tmp/path.txt")

    with pytest.raises(
        HyperbrowserError, match="file_path must resolve to a string path"
    ) as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


def test_ensure_existing_file_path_rejects_string_subclass_path_inputs_before_contains():
    class _BrokenPath(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __contains__(self, item):  # type: ignore[override]
            _ = item
            raise RuntimeError("path contains exploded")

    with pytest.raises(
        HyperbrowserError, match="file_path must resolve to a string path"
    ) as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


def test_ensure_existing_file_path_rejects_string_subclass_path_inputs_before_character_iteration():
    class _BrokenPath(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __contains__(self, item):  # type: ignore[override]
            _ = item
            return False

        def __iter__(self):
            raise RuntimeError("path iteration exploded")

    with pytest.raises(
        HyperbrowserError, match="file_path must resolve to a string path"
    ) as exc_info:
        ensure_existing_file_path(
            _BrokenPath("/tmp/path.txt"),
            missing_file_message="missing",
            not_file_message="not-file",
        )

    assert exc_info.value.original_error is None


def test_open_binary_file_reads_content_and_closes(tmp_path: Path):
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(b"content")

    with open_binary_file(
        str(file_path),
        open_error_message="open failed",
    ) as file_obj:
        assert file_obj.read() == b"content"
        assert file_obj.closed is False

    assert file_obj.closed is True


def test_open_binary_file_rejects_non_string_error_message(tmp_path: Path):
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(b"content")

    with pytest.raises(HyperbrowserError, match="open_error_message must be a string"):
        with open_binary_file(
            str(file_path),
            open_error_message=123,  # type: ignore[arg-type]
        ):
            pass


def test_open_binary_file_rejects_invalid_file_path_type():
    with pytest.raises(
        HyperbrowserError, match="file_path must be a string or os.PathLike object"
    ):
        with open_binary_file(
            123,  # type: ignore[arg-type]
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_rejects_non_string_fspath_results():
    with pytest.raises(HyperbrowserError, match="file_path must resolve to a string"):
        with open_binary_file(
            b"/tmp/bytes-path",  # type: ignore[arg-type]
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_wraps_fspath_runtime_errors():
    class _BrokenPathLike:
        def __fspath__(self) -> str:
            raise RuntimeError("bad fspath")

    with pytest.raises(HyperbrowserError, match="file_path is invalid") as exc_info:
        with open_binary_file(
            _BrokenPathLike(),  # type: ignore[arg-type]
            open_error_message="open failed",
        ):
            pass

    assert exc_info.value.original_error is not None


def test_open_binary_file_preserves_hyperbrowser_fspath_errors():
    class _BrokenPathLike:
        def __fspath__(self) -> str:
            raise HyperbrowserError("custom fspath failure")

    with pytest.raises(HyperbrowserError, match="custom fspath failure") as exc_info:
        with open_binary_file(
            _BrokenPathLike(),  # type: ignore[arg-type]
            open_error_message="open failed",
        ):
            pass

    assert exc_info.value.original_error is None


def test_open_binary_file_rejects_string_subclass_fspath_results():
    class _PathLike:
        class _PathString(str):
            pass

        def __fspath__(self):
            return self._PathString("/tmp/subclass-path")

    with pytest.raises(HyperbrowserError, match="file_path must resolve to a string"):
        with open_binary_file(
            _PathLike(),  # type: ignore[arg-type]
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_rejects_empty_string_paths():
    with pytest.raises(HyperbrowserError, match="file_path must not be empty"):
        with open_binary_file(
            "",
            open_error_message="open failed",
        ):
            pass
    with pytest.raises(HyperbrowserError, match="file_path must not be empty"):
        with open_binary_file(
            "   ",
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_rejects_surrounding_whitespace():
    with pytest.raises(
        HyperbrowserError,
        match="file_path must not contain leading or trailing whitespace",
    ):
        with open_binary_file(
            " /tmp/file.txt",
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_rejects_null_byte_paths():
    with pytest.raises(
        HyperbrowserError, match="file_path must not contain null bytes"
    ):
        with open_binary_file(
            "bad\x00path.txt",
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_rejects_control_character_paths():
    with pytest.raises(
        HyperbrowserError, match="file_path must not contain control characters"
    ):
        with open_binary_file(
            "bad\tpath.txt",
            open_error_message="open failed",
        ):
            pass


def test_open_binary_file_wraps_open_errors(tmp_path: Path):
    missing_path = tmp_path / "missing.bin"

    with pytest.raises(HyperbrowserError, match="open failed") as exc_info:
        with open_binary_file(
            str(missing_path),
            open_error_message="open failed",
        ):
            pass

    assert isinstance(exc_info.value.original_error, FileNotFoundError)
