import os
from pathlib import Path
from typing import Any, Dict, IO, Union

from ...exceptions import HyperbrowserError
from ...transport.base import RequestBuilder, prepare_request

UploadInput = Union[str, os.PathLike, IO[bytes], bytes, bytearray]


def build_extension_upload_request(
    data: Dict[str, Any], file_path: Union[str, os.PathLike]
) -> RequestBuilder:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Extension file not found at path: {path}")

    file_bytes = path.read_bytes()
    filename = path.name or "extension.zip"

    def builder():
        return prepare_request(
            data=data,
            files={"file": (filename, file_bytes, "application/zip")},
            replayable=True,
        )

    return builder


def build_session_upload_request(file_input: UploadInput) -> RequestBuilder:
    if isinstance(file_input, (str, os.PathLike)):
        return _build_path_upload_request(Path(file_input))

    if isinstance(file_input, (bytes, bytearray)):
        payload = bytes(file_input)

        def builder():
            return prepare_request(
                files={
                    "file": ("upload.bin", payload, "application/octet-stream"),
                },
                replayable=True,
            )

        return builder

    if hasattr(file_input, "read"):
        filename = _infer_upload_filename(file_input)

        def builder():
            return prepare_request(
                files={"file": (filename, file_input)},
                replayable=False,
            )

        return builder

    raise TypeError(
        "file_input must be a file path, a bytes-like object, or a binary file-like object"
    )


def _build_path_upload_request(path: Path) -> RequestBuilder:
    try:
        path.stat()
    except OSError as error:
        _raise_upload_read_failed(path, error)

    filename = path.name or "upload.bin"

    def builder():
        try:
            file_obj = path.open("rb")
        except OSError as error:
            _raise_upload_read_failed(path, error)

        return prepare_request(
            files={"file": (filename, file_obj, "application/octet-stream")},
            replayable=True,
            closeables=[file_obj],
        )

    return builder


def _infer_upload_filename(file_obj: IO[bytes]) -> str:
    raw_name = getattr(file_obj, "name", "")
    if isinstance(raw_name, os.PathLike):
        raw_name = os.fspath(raw_name)
    if isinstance(raw_name, str):
        filename = Path(raw_name).name
        if filename:
            return filename
    return "upload.bin"


def _raise_upload_read_failed(path: Path, error: OSError) -> None:
    raise HyperbrowserError(
        f"Failed to read upload file at path: {path}",
        code="file_upload_read_failed",
        retryable=False,
        service="control",
        cause=error,
        original_error=error,
    )
