import base64
import json
import socket
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, Optional, Union
from urllib.parse import urlencode

import httpx
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect as sync_ws_connect

from ....exceptions import HyperbrowserError
from ....models.sandbox import (
    CreateSandboxParams,
    SandboxDetail,
    SandboxExecParams,
    SandboxFileChmodParams,
    SandboxFileChownParams,
    SandboxFileEntry,
    SandboxFileDeleteParams,
    SandboxFileListResponse,
    SandboxFileMoveCopyResult,
    SandboxFileMutationResult,
    SandboxFileReadResult,
    SandboxFileTransferResult,
    SandboxFileWatchDoneEvent,
    SandboxFileWatchEventMessage,
    SandboxFileWatchStatus,
    SandboxListParams,
    SandboxListResponse,
    SandboxPresignFileParams,
    SandboxPresignedUrl,
    SandboxProcessExitEvent,
    SandboxProcessListResponse,
    SandboxProcessOutputEvent,
    SandboxProcessResult,
    SandboxProcessStdinParams,
    SandboxProcessSummary,
    SandboxRuntimeSession,
    SandboxTerminalCreateParams,
    SandboxTerminalExitEvent,
    SandboxTerminalOutputEvent,
    SandboxTerminalStatus,
    SandboxTerminalWaitParams,
    StartSandboxFromSnapshotParams,
)
from ....models.session import BasicResponse
from ....sandbox_common import (
    RUNTIME_SESSION_REFRESH_BUFFER_MS,
    RuntimeConnection,
    build_headers,
    ensure_response_ok,
    normalize_network_error,
    parse_error_payload,
    parse_json_response,
    resolve_runtime_transport_target,
    to_websocket_transport_target,
)

DEFAULT_PROCESS_KILL_WAIT_SECONDS = 5.0
DEFAULT_TERMINAL_KILL_WAIT_SECONDS = 5.0


def _copy_model(model):
    return model.model_copy(deep=True)


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


class RuntimeTransport:
    def __init__(self, resolve_connection, timeout: float = 30.0):
        self._resolve_connection = resolve_connection
        self._timeout = timeout

    def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        json_body: Optional[Dict[str, object]] = None,
        content: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        response = self._request(
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )
        return parse_json_response(response, "runtime")

    def request_bytes(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bytes:
        response = self._request(path, method=method, params=params, headers=headers)
        return response.content

    def stream_sse(
        self, path: str, params: Optional[Dict[str, object]] = None
    ) -> Iterator[Dict[str, object]]:
        client, response = self._open_stream(path, params=params)
        event_name = "message"
        event_id = None
        data_lines = []

        def flush_event():
            nonlocal event_name, event_id, data_lines
            if not data_lines and event_name == "message" and event_id is None:
                return None

            raw_data = "\n".join(data_lines)
            data = raw_data
            if raw_data:
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    data = raw_data

            event = {
                "event": event_name,
                "data": data,
                "id": event_id,
            }
            event_name = "message"
            event_id = None
            data_lines = []
            return event

        try:
            for line in response.iter_lines():
                if line == "":
                    event = flush_event()
                    if event is not None:
                        yield event
                    continue

                if line.startswith(":"):
                    continue

                if ":" in line:
                    field, value = line.split(":", 1)
                    value = value.lstrip(" ")
                else:
                    field, value = line, ""

                if field == "event":
                    event_name = value or "message"
                elif field == "data":
                    data_lines.append(value)
                elif field == "id":
                    event_id = value

            trailing = flush_event()
            if trailing is not None:
                yield trailing
        finally:
            response.close()
            client.close()

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        json_body: Optional[Dict[str, object]] = None,
        content: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_refresh: bool = True,
    ) -> httpx.Response:
        connection = self._resolve_connection(False)
        response = self._send(
            connection,
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )

        if response.status_code == 401 and allow_refresh:
            response.close()
            refreshed = self._resolve_connection(True)
            retry = self._send(
                refreshed,
                path,
                method=method,
                params=params,
                json_body=json_body,
                content=content,
                headers=headers,
            )
            return ensure_response_ok(retry, "runtime")

        return ensure_response_ok(response, "runtime")

    def _open_stream(
        self,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        allow_refresh: bool = True,
    ):
        connection = self._resolve_connection(False)
        client, response = self._send_stream(connection, path, params=params)
        if response.status_code == 401 and allow_refresh:
            response.close()
            client.close()
            refreshed = self._resolve_connection(True)
            client, response = self._send_stream(refreshed, path, params=params)

        if not response.is_success:
            response.read()
        ensure_response_ok(response, "runtime")
        return client, response

    def _send(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        method: str,
        params: Optional[Dict[str, object]],
        json_body: Optional[Dict[str, object]],
        content: Optional[Union[str, bytes]],
        headers: Optional[Dict[str, str]],
    ) -> httpx.Response:
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(connection.base_url, request_path)
        merged_headers = build_headers(connection.token, headers, target.host_header)
        client = httpx.Client(timeout=self._timeout)

        try:
            response = client.request(
                method,
                target.url,
                headers=merged_headers,
                json=json_body,
                content=content,
            )
        except BaseException as error:
            client.close()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
            )

        response.read()
        client.close()
        return response

    def _send_stream(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        params: Optional[Dict[str, object]],
    ):
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(connection.base_url, request_path)
        headers = build_headers(
            connection.token,
            {"Accept": "text/event-stream"},
            target.host_header,
        )
        client = httpx.Client(timeout=self._timeout)

        try:
            request = client.build_request("GET", target.url, headers=headers)
            response = client.send(request, stream=True)
            return client, response
        except BaseException as error:
            client.close()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
            )


class SandboxProcessHandle:
    def __init__(self, transport: RuntimeTransport, summary: SandboxProcessSummary):
        self._transport = transport
        self._summary = summary

    @property
    def id(self) -> str:
        return self._summary.id

    @property
    def status(self) -> str:
        return self._summary.status

    def to_dict(self):
        return self._summary.model_dump()

    def to_json(self):
        return self.to_dict()

    def refresh(self) -> "SandboxProcessHandle":
        payload = self._transport.request_json(f"/sandbox/processes/{self.id}")
        self._summary = SandboxProcessSummary(**payload["process"])
        return self

    def wait(self, timeout_ms: Optional[int] = None, timeout_sec: Optional[int] = None):
        payload = self._transport.request_json(
            f"/sandbox/processes/{self.id}/wait",
            method="POST",
            json_body={
                "timeoutMs": timeout_ms,
                "timeout_sec": timeout_sec,
            },
            headers={"content-type": "application/json"},
        )
        result = SandboxProcessResult(**payload["result"])
        self._summary = SandboxProcessSummary(
            id=result.id,
            status=result.status,
            command=self._summary.command,
            args=self._summary.args,
            cwd=self._summary.cwd,
            pid=self._summary.pid,
            exit_code=result.exit_code,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )
        return result

    def signal(self, signal: str) -> None:
        payload = self._transport.request_json(
            f"/sandbox/processes/{self.id}/signal",
            method="POST",
            json_body={"signal": signal},
            headers={"content-type": "application/json"},
        )
        self._summary = SandboxProcessSummary(**payload["process"])

    def kill(
        self,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
    ) -> SandboxProcessResult:
        payload = self._transport.request_json(
            f"/sandbox/processes/{self.id}",
            method="DELETE",
        )
        self._summary = SandboxProcessSummary(**payload["process"])
        if timeout_ms is None and timeout_sec is None:
            timeout_ms = int(DEFAULT_PROCESS_KILL_WAIT_SECONDS * 1000)
        return self.wait(timeout_ms=timeout_ms, timeout_sec=timeout_sec)

    def write_stdin(
        self,
        data: Optional[Union[str, bytes, bytearray, SandboxProcessStdinParams]] = None,
        *,
        encoding: Optional[str] = None,
        eof: Optional[bool] = None,
    ) -> None:
        if isinstance(data, SandboxProcessStdinParams):
            params = data
        else:
            params = SandboxProcessStdinParams(data=data, encoding=encoding, eof=eof)

        payload: Dict[str, object] = {"eof": params.eof}
        if params.data is not None:
            if isinstance(params.data, str):
                payload["data"] = params.data
                payload["encoding"] = params.encoding or "utf8"
            else:
                payload["data"] = base64.b64encode(bytes(params.data)).decode("ascii")
                payload["encoding"] = "base64"

        self._transport.request_json(
            f"/sandbox/processes/{self.id}/stdin",
            method="POST",
            json_body=payload,
            headers={"content-type": "application/json"},
        )

    def stream(self, from_seq: Optional[int] = None):
        params = {"from_seq": from_seq} if from_seq and from_seq > 0 else None
        for event in self._transport.stream_sse(
            f"/sandbox/processes/{self.id}/stream",
            params=params,
        ):
            event_type = event["event"]
            data = event["data"]
            if event_type == "output":
                yield SandboxProcessOutputEvent(
                    type=data["stream"],
                    seq=data["seq"],
                    data=data["data"],
                    timestamp=data["timestamp"],
                )
            elif event_type == "done":
                yield SandboxProcessExitEvent(
                    type="exit",
                    result=SandboxProcessResult(**data),
                )

    def result(self) -> SandboxProcessResult:
        return self.wait()


class SandboxProcessesApi:
    def __init__(self, transport: RuntimeTransport):
        self._transport = transport

    def exec(self, input: Union[SandboxExecParams, Dict[str, object]]) -> SandboxProcessResult:
        params = input if isinstance(input, SandboxExecParams) else SandboxExecParams(**input)
        payload = self._transport.request_json(
            "/sandbox/exec",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxProcessResult(**payload["result"])

    def start(self, input: Union[SandboxExecParams, Dict[str, object]]) -> SandboxProcessHandle:
        params = input if isinstance(input, SandboxExecParams) else SandboxExecParams(**input)
        payload = self._transport.request_json(
            "/sandbox/processes",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxProcessHandle(
            self._transport,
            SandboxProcessSummary(**payload["process"]),
        )

    def get(self, process_id: str) -> SandboxProcessHandle:
        payload = self._transport.request_json(f"/sandbox/processes/{process_id}")
        return SandboxProcessHandle(
            self._transport,
            SandboxProcessSummary(**payload["process"]),
        )

    def list(
        self,
        *,
        status=None,
        limit: Optional[int] = None,
        cursor: Optional[Union[str, int]] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
    ) -> SandboxProcessListResponse:
        normalized_status = None
        if isinstance(status, list):
            normalized_status = ",".join(status) if status else None
        else:
            normalized_status = status

        payload = self._transport.request_json(
            "/sandbox/processes",
            params={
                "status": normalized_status,
                "limit": limit,
                "cursor": cursor,
                "created_after": created_after,
                "created_before": created_before,
            },
        )
        return SandboxProcessListResponse(**payload)


class SandboxFileWatchHandle:
    def __init__(self, transport: RuntimeTransport, get_connection_info, status):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._status = status

    @property
    def id(self) -> str:
        return self._status.id

    @property
    def current(self) -> SandboxFileWatchStatus:
        return _copy_model(self._status)

    def to_dict(self):
        return self._status.model_dump()

    def to_json(self):
        return self.to_dict()

    def refresh(self, include_events: bool = False) -> "SandboxFileWatchHandle":
        params = {"includeEvents": True} if include_events else None
        payload = self._transport.request_json(
            f"/sandbox/files/watch/{self.id}",
            params=params,
        )
        self._status = SandboxFileWatchStatus(**payload["watch"])
        return self

    def stop(self) -> None:
        self._transport.request_json(
            f"/sandbox/files/watch/{self.id}",
            method="DELETE",
        )
        self._status = self._status.model_copy(
            update={
                "active": False,
                "stopped_at": self._status.stopped_at or int(datetime.now().timestamp() * 1000),
            }
        )

    def events(
        self,
        *,
        cursor: Optional[int] = None,
        route: str = "ws",
    ):
        connection = self._get_connection_info()
        query = urlencode(
            [
                ("sessionId", connection.sandbox_id),
                *([("cursor", str(cursor))] if cursor is not None else []),
            ]
        )
        target = to_websocket_transport_target(
            connection.base_url,
            f"/sandbox/files/watch/{self.id}/{route}?{query}",
        )
        headers = build_headers(connection.token, host_header=target.host_header)
        connect_kwargs = {}
        if target.connect_host is not None and target.connect_port is not None:
            connect_kwargs["sock"] = socket.create_connection(
                (target.connect_host, target.connect_port),
                timeout=self._transport._timeout,
            )
        try:
            websocket = sync_ws_connect(
                target.url,
                additional_headers=headers,
                open_timeout=self._transport._timeout,
                **connect_kwargs,
            )
        except BaseException as error:
            raise _normalize_websocket_error(error)

        try:
            while True:
                try:
                    message = websocket.recv()
                except ConnectionClosed:
                    break

                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                parsed = json.loads(message)
                if parsed["type"] == "event":
                    event = SandboxFileWatchEventMessage(
                        type="event",
                        event=parsed["event"],
                    )
                    self._status = self._status.model_copy(
                        update={
                            "oldest_seq": self._status.oldest_seq or event.event.seq,
                            "last_seq": max(self._status.last_seq, event.event.seq),
                        }
                    )
                    yield event
                elif parsed["type"] == "done":
                    self._status = SandboxFileWatchStatus(**parsed["status"])
                    yield SandboxFileWatchDoneEvent(type="done", status=self.current)
                    break
        except GeneratorExit:
            raise
        except BaseException as error:
            raise _normalize_websocket_error(error)
        finally:
            websocket.close()


class SandboxFilesApi:
    def __init__(self, transport: RuntimeTransport, get_connection_info):
        self._transport = transport
        self._get_connection_info = get_connection_info

    def list(
        self,
        path: str,
        *,
        recursive: Optional[bool] = None,
        limit: Optional[int] = None,
        cursor: Optional[int] = None,
    ) -> SandboxFileListResponse:
        payload = self._transport.request_json(
            "/sandbox/files",
            params={
                "path": path,
                "recursive": recursive,
                "limit": limit,
                "cursor": cursor,
            },
        )
        return SandboxFileListResponse(**payload)

    def stat(self, path: str):
        payload = self._transport.request_json(
            "/sandbox/files/stat",
            params={"path": path},
        )
        return SandboxFileEntry(**payload["file"])

    def exists(self, path: str) -> bool:
        try:
            self.stat(path)
            return True
        except HyperbrowserError as error:
            if error.status_code == 404:
                return False
            if "not found" in str(error).lower() or "no such file" in str(error).lower():
                return False
            raise

    def read(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
        encoding: str = "utf8",
    ) -> SandboxFileReadResult:
        payload = self._transport.request_json(
            "/sandbox/files/read",
            method="POST",
            json_body={
                "path": path,
                "offset": offset,
                "length": length,
                "encoding": encoding,
            },
            headers={"content-type": "application/json"},
        )
        return SandboxFileReadResult(**payload)

    def read_text(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> str:
        return self.read(path, offset=offset, length=length, encoding="utf8").content

    def read_bytes(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> bytes:
        result = self.read(path, offset=offset, length=length, encoding="base64")
        return base64.b64decode(result.content)

    def write_text(
        self,
        path: str,
        data: str,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
    ):
        return self._write(
            path,
            data,
            append=append,
            mode=mode,
            encoding="utf8",
        )

    def write_bytes(
        self,
        path: str,
        data: bytes,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
    ):
        return self._write(
            path,
            base64.b64encode(data).decode("ascii"),
            append=append,
            mode=mode,
            encoding="base64",
        )

    def upload(self, path: str, data: Union[str, bytes, bytearray]):
        body = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        payload = self._transport.request_json(
            "/sandbox/files/upload",
            method="PUT",
            params={"path": path},
            content=body,
        )
        return SandboxFileTransferResult(**payload)

    def download(self, path: str) -> bytes:
        return self._transport.request_bytes(
            "/sandbox/files/download",
            params={"path": path},
        )

    def delete(self, path: str, *, recursive: Optional[bool] = None):
        payload = self._transport.request_json(
            "/sandbox/files/delete",
            method="POST",
            json_body=SandboxFileDeleteParams(
                path=path,
                recursive=recursive,
            ).model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )
        return SandboxFileMutationResult(**payload)

    def mkdir(
        self,
        path: str,
        *,
        parents: Optional[bool] = None,
        mode: Optional[str] = None,
    ):
        payload = self._transport.request_json(
            "/sandbox/files/mkdir",
            method="POST",
            json_body={
                "path": path,
                "parents": parents,
                "mode": mode,
            },
            headers={"content-type": "application/json"},
        )
        return SandboxFileMutationResult(**payload)

    def move(
        self,
        *,
        source: str,
        destination: str,
        overwrite: Optional[bool] = None,
    ) -> SandboxFileMoveCopyResult:
        payload = self._transport.request_json(
            "/sandbox/files/move",
            method="POST",
            json_body={
                "from": source,
                "to": destination,
                "overwrite": overwrite,
            },
            headers={"content-type": "application/json"},
        )
        return SandboxFileMoveCopyResult(**payload)

    def copy(
        self,
        *,
        source: str,
        destination: str,
        recursive: Optional[bool] = None,
        overwrite: Optional[bool] = None,
    ) -> SandboxFileMoveCopyResult:
        payload = self._transport.request_json(
            "/sandbox/files/copy",
            method="POST",
            json_body={
                "from": source,
                "to": destination,
                "recursive": recursive,
                "overwrite": overwrite,
            },
            headers={"content-type": "application/json"},
        )
        return SandboxFileMoveCopyResult(**payload)

    def chmod(self, *, path: str, mode: str, recursive: Optional[bool] = None):
        payload = self._transport.request_json(
            "/sandbox/files/chmod",
            method="POST",
            json_body=SandboxFileChmodParams(
                path=path,
                mode=mode,
                recursive=recursive,
            ).model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )
        return SandboxFileMutationResult(**payload)

    def chown(
        self,
        *,
        path: str,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        recursive: Optional[bool] = None,
    ):
        payload = self._transport.request_json(
            "/sandbox/files/chown",
            method="POST",
            json_body=SandboxFileChownParams(
                path=path,
                uid=uid,
                gid=gid,
                recursive=recursive,
            ).model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )
        return SandboxFileMutationResult(**payload)

    def watch(self, path: str, *, recursive: Optional[bool] = None):
        payload = self._transport.request_json(
            "/sandbox/files/watch",
            method="POST",
            json_body={
                "path": path,
                "recursive": recursive,
            },
            headers={"content-type": "application/json"},
        )
        return SandboxFileWatchHandle(
            self._transport,
            self._get_connection_info,
            SandboxFileWatchStatus(**payload["watch"]),
        )

    def get_watch(
        self, watch_id: str, include_events: bool = False
    ) -> SandboxFileWatchHandle:
        payload = self._transport.request_json(
            f"/sandbox/files/watch/{watch_id}",
            params={"includeEvents": True} if include_events else None,
        )
        return SandboxFileWatchHandle(
            self._transport,
            self._get_connection_info,
            SandboxFileWatchStatus(**payload["watch"]),
        )

    def upload_url(
        self,
        path: str,
        *,
        expires_in_seconds: Optional[int] = None,
        one_time: Optional[bool] = None,
    ) -> SandboxPresignedUrl:
        payload = self._transport.request_json(
            "/sandbox/files/presign-upload",
            method="POST",
            json_body=SandboxPresignFileParams(
                path=path,
                expires_in_seconds=expires_in_seconds,
                one_time=one_time,
            ).model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxPresignedUrl(**payload)

    def download_url(
        self,
        path: str,
        *,
        expires_in_seconds: Optional[int] = None,
        one_time: Optional[bool] = None,
    ) -> SandboxPresignedUrl:
        payload = self._transport.request_json(
            "/sandbox/files/presign-download",
            method="POST",
            json_body=SandboxPresignFileParams(
                path=path,
                expires_in_seconds=expires_in_seconds,
                one_time=one_time,
            ).model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxPresignedUrl(**payload)

    def _write(
        self,
        path: str,
        data: str,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
        encoding: str,
    ):
        payload = self._transport.request_json(
            "/sandbox/files/write",
            method="POST",
            json_body={
                "path": path,
                "data": data,
                "append": append,
                "mode": mode,
                "encoding": encoding,
            },
            headers={"content-type": "application/json"},
        )
        return SandboxFileTransferResult(**payload)


class SandboxTerminalConnection:
    def __init__(self, websocket):
        self._websocket = websocket

    def events(self):
        while True:
            try:
                message = self._websocket.recv()
            except ConnectionClosed:
                break

            if isinstance(message, bytes):
                message = message.decode("utf-8")
            parsed = json.loads(message)
            if parsed["type"] == "output":
                raw = base64.b64decode(parsed["data"])
                yield SandboxTerminalOutputEvent(
                    type="output",
                    seq=parsed["seq"],
                    data=raw.decode("utf-8", errors="replace"),
                    raw=raw,
                    timestamp=parsed["timestamp"],
                )
            elif parsed["type"] == "exit":
                yield SandboxTerminalExitEvent(
                    type="exit",
                    status=SandboxTerminalStatus(**parsed["status"]),
                )

    def write(self, data: Union[str, bytes, bytearray]) -> None:
        payload = {
            "type": "input",
            "data": data if isinstance(data, str) else base64.b64encode(bytes(data)).decode("ascii"),
        }
        if not isinstance(data, str):
            payload["encoding"] = "base64"
        self._websocket.send(json.dumps(payload))

    def resize(self, rows: int, cols: int) -> None:
        self._websocket.send(
            json.dumps(
                {
                    "type": "resize",
                    "rows": rows,
                    "cols": cols,
                }
            )
        )

    def close(self) -> None:
        self._websocket.close()


class SandboxTerminalHandle:
    def __init__(self, transport: RuntimeTransport, get_connection_info, status):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._status = status

    @property
    def id(self) -> str:
        return self._status.id

    @property
    def current(self) -> SandboxTerminalStatus:
        return _copy_model(self._status)

    def to_dict(self):
        return self._status.model_dump()

    def to_json(self):
        return self.to_dict()

    def refresh(self, include_output: bool = False) -> "SandboxTerminalHandle":
        payload = self._transport.request_json(
            f"/sandbox/pty/{self.id}",
            params={"includeOutput": True} if include_output else None,
        )
        self._status = SandboxTerminalStatus(**payload["pty"])
        return self

    def wait(
        self,
        timeout_ms: Optional[int] = None,
        include_output: Optional[bool] = None,
    ) -> SandboxTerminalStatus:
        payload = self._transport.request_json(
            f"/sandbox/pty/{self.id}/wait",
            method="POST",
            json_body=SandboxTerminalWaitParams(
                timeout_ms=timeout_ms,
                include_output=include_output,
            ).model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        self._status = SandboxTerminalStatus(**payload["pty"])
        return self.current

    def signal(self, signal: Optional[str] = None) -> SandboxTerminalStatus:
        payload = self._transport.request_json(
            f"/sandbox/pty/{self.id}/kill",
            method="POST",
            json_body={"signal": signal},
            headers={"content-type": "application/json"},
        )
        self._status = SandboxTerminalStatus(**payload["pty"])
        return self.current

    def kill(
        self,
        signal: Optional[str] = None,
        *,
        timeout_ms: Optional[int] = None,
    ) -> SandboxTerminalStatus:
        self.signal(signal)
        if timeout_ms is None:
            timeout_ms = int(DEFAULT_TERMINAL_KILL_WAIT_SECONDS * 1000)
        return self.wait(timeout_ms=timeout_ms)

    def resize(self, rows: int, cols: int) -> SandboxTerminalStatus:
        payload = self._transport.request_json(
            f"/sandbox/pty/{self.id}/resize",
            method="POST",
            json_body={"rows": rows, "cols": cols},
            headers={"content-type": "application/json"},
        )
        self._status = SandboxTerminalStatus(**payload["pty"])
        return self.current

    def attach(self) -> SandboxTerminalConnection:
        connection = self._get_connection_info()
        target = to_websocket_transport_target(
            connection.base_url,
            f"/sandbox/pty/{self.id}/ws?sessionId={connection.sandbox_id}",
        )
        headers = build_headers(connection.token, host_header=target.host_header)
        connect_kwargs = {}
        if target.connect_host is not None and target.connect_port is not None:
            connect_kwargs["sock"] = socket.create_connection(
                (target.connect_host, target.connect_port),
                timeout=self._transport._timeout,
            )

        try:
            websocket = sync_ws_connect(
                target.url,
                additional_headers=headers,
                open_timeout=self._transport._timeout,
                **connect_kwargs,
            )
        except BaseException as error:
            raise _normalize_websocket_error(error)

        return SandboxTerminalConnection(websocket)


class SandboxTerminalApi:
    def __init__(self, transport: RuntimeTransport, get_connection_info):
        self._transport = transport
        self._get_connection_info = get_connection_info

    def create(
        self,
        input: Union[SandboxTerminalCreateParams, Dict[str, object]],
    ) -> SandboxTerminalHandle:
        params = (
            input
            if isinstance(input, SandboxTerminalCreateParams)
            else SandboxTerminalCreateParams(**input)
        )
        payload = self._transport.request_json(
            "/sandbox/pty",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxTerminalHandle(
            self._transport,
            self._get_connection_info,
            SandboxTerminalStatus(**payload["pty"]),
        )

    def get(self, terminal_id: str, include_output: bool = False) -> SandboxTerminalHandle:
        payload = self._transport.request_json(
            f"/sandbox/pty/{terminal_id}",
            params={"includeOutput": True} if include_output else None,
        )
        return SandboxTerminalHandle(
            self._transport,
            self._get_connection_info,
            SandboxTerminalStatus(**payload["pty"]),
        )


class SandboxHandle:
    def __init__(self, service: "SandboxManager", detail: SandboxDetail):
        self._service = service
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)
        self._transport = RuntimeTransport(
            self._resolve_runtime_connection,
            service.runtime_timeout,
        )
        self.processes = SandboxProcessesApi(self._transport)
        self.files = SandboxFilesApi(self._transport, self._resolve_runtime_socket_info)
        self.terminal = SandboxTerminalApi(
            self._transport,
            self._resolve_runtime_socket_info,
        )
        self.pty = self.terminal

    @property
    def id(self) -> str:
        return self._detail.id

    @property
    def status(self) -> str:
        return self._detail.status

    @property
    def region(self):
        return self._detail.region

    @property
    def runtime(self):
        return self._detail.runtime

    @property
    def token_expires_at(self):
        return self._detail.token_expires_at

    @property
    def session_url(self) -> str:
        return self._detail.session_url

    def to_dict(self):
        return self._detail.model_dump()

    def to_json(self):
        return self.to_dict()

    def info(self) -> SandboxDetail:
        detail = self._service.get_detail(self.id)
        self._hydrate(detail)
        return _copy_model(self._detail)

    def refresh(self) -> "SandboxHandle":
        self.info()
        return self

    def connect(self) -> "SandboxHandle":
        self.create_runtime_session(force_refresh=True)
        return self

    def stop(self) -> BasicResponse:
        response = self._service.stop(self.id)
        self._clear_runtime_session("closed")
        return response

    def create_runtime_session(
        self, force_refresh: bool = False
    ) -> SandboxRuntimeSession:
        self._assert_runtime_available()
        if (
            not force_refresh
            and self._runtime_session is not None
            and not _expires_within_buffer(self._runtime_session.token_expires_at)
        ):
            return _copy_model(self._runtime_session)

        session = self._service.get_runtime_session(self.id)
        self._apply_runtime_session(session)
        return _copy_model(session)

    def exec(self, input: Union[str, SandboxExecParams, Dict[str, object]]):
        if isinstance(input, str):
            params = SandboxExecParams(command=input)
        elif isinstance(input, SandboxExecParams):
            params = input
        else:
            params = SandboxExecParams(**input)
        return self.processes.exec(params)

    def get_process(self, process_id: str) -> SandboxProcessHandle:
        return self.processes.get(process_id)

    def _hydrate(self, detail: SandboxDetail) -> None:
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)

    def _resolve_runtime_connection(self, force_refresh: bool = False) -> RuntimeConnection:
        session = self.create_runtime_session(force_refresh=force_refresh)
        return RuntimeConnection(
            sandbox_id=self.id,
            base_url=session.runtime.base_url,
            token=session.token,
        )

    def _resolve_runtime_socket_info(self) -> RuntimeConnection:
        session = self.create_runtime_session()
        return RuntimeConnection(
            sandbox_id=self.id,
            base_url=session.runtime.base_url,
            token=session.token,
        )

    def _apply_runtime_session(self, session: SandboxRuntimeSession) -> None:
        self._runtime_session = _copy_model(session)
        self._detail = self._detail.model_copy(
            update={
                "status": session.status,
                "region": session.region,
                "runtime": session.runtime,
                "token": session.token,
                "token_expires_at": session.token_expires_at,
            }
        )

    def _clear_runtime_session(self, status: Optional[str] = None) -> None:
        self._runtime_session = None
        self._detail = self._detail.model_copy(
            update={
                "status": status or self._detail.status,
                "token": None,
                "token_expires_at": None,
            }
        )

    def _assert_runtime_available(self) -> None:
        if self._detail.status in {"closed", "error"}:
            raise HyperbrowserError(
                f"Sandbox {self.id} is not running",
                status_code=409,
                code="sandbox_not_running",
                retryable=False,
                service="runtime",
            )

    @staticmethod
    def _to_runtime_session(detail: SandboxDetail) -> Optional[SandboxRuntimeSession]:
        if not detail.token:
            return None
        return SandboxRuntimeSession(
            sandbox_id=detail.id,
            status=detail.status,
            region=detail.region,
            token=detail.token,
            token_expires_at=detail.token_expires_at,
            runtime=detail.runtime,
        )


class SandboxManager:
    def __init__(self, client):
        self._client = client
        self.runtime_timeout = getattr(client, "timeout", 30)

    def create(self, params: CreateSandboxParams) -> SandboxHandle:
        detail = self._create_detail(params)
        return self.attach(detail)

    def start_from_snapshot(
        self, params: StartSandboxFromSnapshotParams
    ) -> SandboxHandle:
        detail = self._start_from_snapshot_detail(params)
        return self.attach(detail)

    def get(self, sandbox_id: str) -> SandboxHandle:
        return self.attach(self.get_detail(sandbox_id))

    def connect(self, sandbox_id: str) -> SandboxHandle:
        sandbox = self.get(sandbox_id)
        sandbox.connect()
        return sandbox

    def list(
        self, params: Optional[SandboxListParams] = None
    ) -> SandboxListResponse:
        payload = self._request(
            "GET",
            "/sandboxes",
            params=(params or SandboxListParams()).model_dump(
                exclude_none=True, by_alias=True
            ),
        )
        return SandboxListResponse(**payload)

    def stop(self, sandbox_id: str) -> BasicResponse:
        payload = self._request("POST", f"/sandboxes/{sandbox_id}/stop")
        return BasicResponse(**payload)

    def get_runtime_session(self, sandbox_id: str) -> SandboxRuntimeSession:
        payload = self._request("POST", f"/sandboxes/{sandbox_id}/runtime-session")
        return SandboxRuntimeSession(**payload)

    def get_detail(self, sandbox_id: str) -> SandboxDetail:
        payload = self._request("GET", f"/sandboxes/{sandbox_id}")
        return SandboxDetail(**payload)

    def attach(self, detail: SandboxDetail) -> SandboxHandle:
        return SandboxHandle(self, detail)

    def _create_detail(self, params: CreateSandboxParams) -> SandboxDetail:
        payload = self._request(
            "POST",
            "/sandboxes",
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SandboxDetail(**payload)

    def _start_from_snapshot_detail(
        self, params: StartSandboxFromSnapshotParams
    ) -> SandboxDetail:
        payload = self._request(
            "POST",
            "/sandboxes/startFromSnapshot",
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SandboxDetail(**payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, object]] = None,
    ):
        try:
            response = self._client.transport.client.request(
                method,
                self._client._build_url(path),
                params={k: v for k, v in (params or {}).items() if v is not None},
                json=data,
            )
        except BaseException as error:
            raise normalize_network_error(
                error,
                "control",
                "Unknown error occurred",
            )

        ensure_response_ok(response, "control")
        return parse_json_response(response, "control")
