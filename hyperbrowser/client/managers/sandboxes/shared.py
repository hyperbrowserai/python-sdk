import base64
import posixpath
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Union
from urllib.parse import urlencode, urlsplit, urlunsplit

from ....exceptions import HyperbrowserError
from ....models.sandbox import (
    SandboxExecParams,
    SandboxFileInfo,
    SandboxFileWriteEntry,
    SandboxFileWriteInfo,
    SandboxTerminalStatus,
)
from ....sandbox_common import (
    RUNTIME_SESSION_REFRESH_BUFFER_MS,
    normalize_network_error,
    parse_error_payload,
)

DEFAULT_WATCH_TIMEOUT_MS = 60_000
SHELL_SAFE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_@%+=:,./-]+$")


def _copy_model(model):
    return model.model_copy(deep=True)


def _quote_shell_token(token: str) -> str:
    if token == "":
        return "''"
    if SHELL_SAFE_TOKEN_PATTERN.fullmatch(token):
        return token
    return "'" + token.replace("'", "'\"'\"'") + "'"


def _normalize_legacy_process_fields(params: SandboxExecParams) -> SandboxExecParams:
    updates = {}

    if params.args:
        updates["command"] = " ".join(
            _quote_shell_token(token) for token in [params.command, *params.args]
        )

    if params.args is not None:
        updates["args"] = None

    if params.use_shell is not None:
        updates["use_shell"] = None

    return params.model_copy(update=updates) if updates else params


def _normalize_exec_params(
    input: Union[str, SandboxExecParams],
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_ms: Optional[int] = None,
    timeout_sec: Optional[int] = None,
    run_as: Optional[str] = None,
) -> SandboxExecParams:
    if isinstance(input, str):
        params = SandboxExecParams(command=input)
    elif isinstance(input, SandboxExecParams):
        params = input
    else:
        raise TypeError("input must be a command string or SandboxExecParams instance")

    updates = {}
    if cwd is not None:
        updates["cwd"] = cwd
    if env is not None:
        updates["env"] = env
    if timeout_ms is not None:
        updates["timeout_ms"] = timeout_ms
    if timeout_sec is not None:
        updates["timeout_sec"] = timeout_sec
    if run_as is not None:
        updates["run_as"] = run_as

    normalized = params.model_copy(update=updates) if updates else params
    return _normalize_legacy_process_fields(normalized)


def _runtime_session_id_from_path(raw_path: str) -> Optional[str]:
    segments = [
        segment for segment in raw_path.strip().strip("/").split("/") if segment
    ]
    if len(segments) < 2 or segments[0] != "sandbox" or not segments[1]:
        return None
    return segments[1]


def _resolve_sandbox_runtime_session_host(runtime, base_url) -> str:
    session_id_from_base_path = _runtime_session_id_from_path(base_url.path)
    if session_id_from_base_path and base_url.hostname:
        return f"{session_id_from_base_path}.{base_url.hostname}"

    runtime_host = str(getattr(runtime, "host", "") or "").strip()
    if runtime_host:
        parsed_host = urlsplit(runtime_host)
        if parsed_host.hostname:
            session_id_from_host_path = _runtime_session_id_from_path(parsed_host.path)
            if session_id_from_host_path:
                return f"{session_id_from_host_path}.{parsed_host.hostname}"
            return parsed_host.hostname
        return runtime_host

    return base_url.hostname or ""


def _build_sandbox_exposed_url(runtime, port: int) -> str:
    parsed = urlsplit(runtime.base_url)
    session_host = _resolve_sandbox_runtime_session_host(runtime, parsed)
    if not session_host:
        return runtime.base_url

    exposed_host = f"{port}-{session_host}"
    netloc = exposed_host
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username:
        credentials = parsed.username
        if parsed.password:
            credentials = f"{credentials}:{parsed.password}"
        netloc = f"{credentials}@{netloc}"

    return urlunsplit((parsed.scheme, netloc, "/", "", ""))


def _expires_within_buffer(expires_at: Optional[datetime]) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    threshold = datetime.now(timezone.utc) + timedelta(
        milliseconds=RUNTIME_SESSION_REFRESH_BUFFER_MS
    )
    return expires_at <= threshold


def _build_query_path(path: str, params: Optional[Dict[str, object]] = None) -> str:
    if not params:
        return path

    filtered = []
    for key, value in params.items():
        if value is None:
            continue
        filtered.append((key, str(value)))

    if not filtered:
        return path

    return f"{path}?{urlencode(filtered)}"


def _normalize_websocket_error(error: BaseException) -> HyperbrowserError:
    if isinstance(error, HyperbrowserError):
        return error

    response = getattr(error, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        headers = getattr(response, "headers", {}) or {}
        body = getattr(response, "body", b"")
        if isinstance(body, memoryview):
            body = body.tobytes()
        if isinstance(body, bytearray):
            body = bytes(body)
        if isinstance(body, bytes):
            raw_text = body.decode("utf-8", errors="replace")
        elif isinstance(body, str):
            raw_text = body
        else:
            raw_text = ""

        message, code, details = parse_error_payload(
            raw_text,
            f"Runtime websocket request failed: {status_code or 0}",
        )
        request_id = None
        if isinstance(headers, dict):
            request_id = headers.get("x-request-id") or headers.get("request-id")
        else:
            request_id = headers.get("x-request-id") or headers.get("request-id")

        return HyperbrowserError(
            message,
            status_code=status_code,
            code=code,
            request_id=request_id,
            retryable=bool(status_code in {429, 502, 503, 504}),
            service="runtime",
            details=details,
            cause=error,
            original_error=error if isinstance(error, Exception) else None,
        )

    status_code = getattr(error, "status_code", None)
    headers = getattr(error, "headers", None)
    if status_code is not None:
        request_id = None
        if headers is not None:
            request_id = headers.get("x-request-id") or headers.get("request-id")
        return HyperbrowserError(
            f"Runtime websocket request failed: {status_code}",
            status_code=status_code,
            request_id=request_id,
            retryable=bool(status_code in {429, 502, 503, 504}),
            service="runtime",
            cause=error,
            original_error=error if isinstance(error, Exception) else None,
        )

    return normalize_network_error(
        error,
        "runtime",
        "Unknown runtime websocket error",
    )


def _normalize_file_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return "dir" if value in {"dir", "directory"} else "file"


def _normalize_file_info(entry: Dict[str, object]) -> SandboxFileInfo:
    normalized = dict(entry)
    normalized["type"] = _normalize_file_type(normalized.get("type"))
    return SandboxFileInfo(**normalized)


def _normalize_write_info(entry: Dict[str, object]) -> SandboxFileWriteInfo:
    normalized = dict(entry)
    normalized["type"] = _normalize_file_type(normalized.get("type"))
    return SandboxFileWriteInfo(**normalized)


def _normalize_event_type(operation: str) -> Optional[str]:
    lower = operation.lower()
    if "chmod" in lower:
        return "chmod"
    if "create" in lower:
        return "create"
    if "remove" in lower or "delete" in lower:
        return "remove"
    if "rename" in lower:
        return "rename"
    if "write" in lower:
        return "write"
    return None


def _relative_watch_name(root: str, absolute_path: str) -> str:
    relative = posixpath.relpath(absolute_path, root)
    if relative in {"", "."}:
        return posixpath.basename(absolute_path)
    return relative


def _encode_write_data(data: Union[str, bytes, bytearray]) -> Dict[str, str]:
    if isinstance(data, str):
        return {
            "data": data,
            "encoding": "utf8",
        }
    return {
        "data": base64.b64encode(bytes(data)).decode("ascii"),
        "encoding": "base64",
    }


def _encode_batch_write_entry(entry: SandboxFileWriteEntry) -> Dict[str, object]:
    if isinstance(entry.data, str):
        encoding = entry.encoding or "utf8"
        if encoding not in {"utf8", "base64"}:
            raise ValueError("encoding should be one of: utf8, base64")
        payload: Dict[str, object] = {
            "path": entry.path,
            "data": entry.data,
            "encoding": encoding,
        }
    else:
        if entry.encoding not in {None, "base64"}:
            raise ValueError("encoding must be base64 when data is bytes")
        payload = {
            "path": entry.path,
            "data": base64.b64encode(bytes(entry.data)).decode("ascii"),
            "encoding": "base64",
        }

    if entry.append is not None:
        payload["append"] = entry.append
    if entry.mode is not None:
        payload["mode"] = entry.mode
    return payload


def _normalize_terminal_output_chunk(entry: Dict[str, object]) -> Dict[str, object]:
    raw = base64.b64decode(entry["data"])
    return {
        "seq": entry["seq"],
        "data": raw.decode("utf-8", errors="replace"),
        "raw": raw,
        "timestamp": entry["timestamp"],
    }


def _normalize_terminal_status(entry: Dict[str, object]) -> SandboxTerminalStatus:
    normalized = dict(entry)
    output = normalized.get("output")
    if isinstance(output, list):
        normalized["output"] = [
            _normalize_terminal_output_chunk(chunk)
            for chunk in output
            if isinstance(chunk, dict)
        ]
    return SandboxTerminalStatus(**normalized)
