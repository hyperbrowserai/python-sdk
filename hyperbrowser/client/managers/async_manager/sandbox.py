import asyncio
import base64
import io
import inspect
import json
import posixpath
import socket
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from websockets.asyncio.client import connect as async_ws_connect
from websockets.exceptions import ConnectionClosed

from ....exceptions import HyperbrowserError
from ....models.sandbox import (
    CreateSandboxParams,
    SandboxDetail,
    SandboxExecParams,
    SandboxFileChmodParams,
    SandboxFileChownParams,
    SandboxFileCopyParams,
    SandboxFileDeleteParams,
    SandboxFileInfo,
    SandboxFileReadResult,
    SandboxFileSystemEvent,
    SandboxFileWriteEntry,
    SandboxFileTransferResult,
    SandboxFileWatchDoneEvent,
    SandboxFileWatchEventMessage,
    SandboxFileWatchStatus,
    SandboxMemorySnapshotParams,
    SandboxMemorySnapshotResult,
    SandboxExposeParams,
    SandboxExposeResult,
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
    parse_json_response,
    resolve_runtime_transport_target,
    to_websocket_transport_target,
)
from ..sync_manager.sandbox import (
    DEFAULT_WATCH_TIMEOUT_MS,
    _build_sandbox_exposed_url,
    _build_query_path,
    _copy_model,
    _encode_write_data,
    _normalize_event_type,
    _normalize_file_info,
    _normalize_terminal_output_chunk,
    _normalize_terminal_status,
    _normalize_websocket_error,
    _normalize_write_info,
    _relative_watch_name,
)

DEFAULT_PROCESS_KILL_WAIT_SECONDS = 5.0
DEFAULT_TERMINAL_KILL_WAIT_SECONDS = 5.0


def _expires_within_buffer(expires_at):
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    threshold = datetime.now(timezone.utc) + timedelta(
        milliseconds=RUNTIME_SESSION_REFRESH_BUFFER_MS
    )
    return expires_at <= threshold


class RuntimeTransport:
    def __init__(
        self,
        resolve_connection,
        timeout: float = 30.0,
        runtime_proxy_override: Optional[str] = None,
    ):
        self._resolve_connection = resolve_connection
        self._timeout = timeout
        self._runtime_proxy_override = runtime_proxy_override

    async def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        json_body: Optional[Dict[str, object]] = None,
        content: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        response = await self._request(
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )
        return parse_json_response(response, "runtime")

    async def request_bytes(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bytes:
        response = await self._request(path, method=method, params=params, headers=headers)
        return response.content

    async def stream_sse(
        self, path: str, params: Optional[Dict[str, object]] = None
    ) -> AsyncIterator[Dict[str, object]]:
        client, response = await self._open_stream(path, params=params)
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
            async for line in response.aiter_lines():
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
            await response.aclose()
            await client.aclose()

    async def _request(
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
        connection = await self._resolve_connection(False)
        response = await self._send(
            connection,
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )

        if response.status_code == 401 and allow_refresh:
            await response.aclose()
            refreshed = await self._resolve_connection(True)
            retry = await self._send(
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

    async def _open_stream(
        self,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        allow_refresh: bool = True,
    ):
        connection = await self._resolve_connection(False)
        client, response = await self._send_stream(connection, path, params=params)
        if response.status_code == 401 and allow_refresh:
            await response.aclose()
            await client.aclose()
            refreshed = await self._resolve_connection(True)
            client, response = await self._send_stream(refreshed, path, params=params)

        if not response.is_success:
            await response.aread()
        ensure_response_ok(response, "runtime")
        return client, response

    async def _send(
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
        target = resolve_runtime_transport_target(
            connection.base_url,
            request_path,
            self._runtime_proxy_override,
        )
        merged_headers = build_headers(connection.token, headers, target.host_header)
        client = httpx.AsyncClient(timeout=self._timeout)

        try:
            response = await client.request(
                method,
                target.url,
                headers=merged_headers,
                json=json_body,
                content=content,
            )
        except BaseException as error:
            await client.aclose()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
            )

        await response.aread()
        await client.aclose()
        return response

    async def _send_stream(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        params: Optional[Dict[str, object]],
    ):
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(
            connection.base_url,
            request_path,
            self._runtime_proxy_override,
        )
        headers = build_headers(
            connection.token,
            {"Accept": "text/event-stream"},
            target.host_header,
        )
        client = httpx.AsyncClient(timeout=self._timeout)

        try:
            request = client.build_request("GET", target.url, headers=headers)
            response = await client.send(request, stream=True)
            return client, response
        except BaseException as error:
            await client.aclose()
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

    async def refresh(self) -> "SandboxProcessHandle":
        payload = await self._transport.request_json(f"/sandbox/processes/{self.id}")
        self._summary = SandboxProcessSummary(**payload["process"])
        return self

    async def wait(
        self,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
    ) -> SandboxProcessResult:
        payload = await self._transport.request_json(
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

    async def signal(self, signal: str) -> None:
        payload = await self._transport.request_json(
            f"/sandbox/processes/{self.id}/signal",
            method="POST",
            json_body={"signal": signal},
            headers={"content-type": "application/json"},
        )
        self._summary = SandboxProcessSummary(**payload["process"])

    async def kill(
        self,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
    ) -> SandboxProcessResult:
        payload = await self._transport.request_json(
            f"/sandbox/processes/{self.id}",
            method="DELETE",
        )
        self._summary = SandboxProcessSummary(**payload["process"])
        if timeout_ms is None and timeout_sec is None:
            timeout_ms = int(DEFAULT_PROCESS_KILL_WAIT_SECONDS * 1000)
        return await self.wait(timeout_ms=timeout_ms, timeout_sec=timeout_sec)

    async def write_stdin(
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

        await self._transport.request_json(
            f"/sandbox/processes/{self.id}/stdin",
            method="POST",
            json_body=payload,
            headers={"content-type": "application/json"},
        )

    async def stream(self, from_seq: Optional[int] = None) -> AsyncIterator[object]:
        params = {"from_seq": from_seq} if from_seq and from_seq > 0 else None
        async for event in self._transport.stream_sse(
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

    async def result(self) -> SandboxProcessResult:
        return await self.wait()


class SandboxProcessesApi:
    def __init__(self, transport: RuntimeTransport):
        self._transport = transport

    async def exec(
        self, input: Union[SandboxExecParams, Dict[str, object]]
    ) -> SandboxProcessResult:
        params = input if isinstance(input, SandboxExecParams) else SandboxExecParams(**input)
        payload = await self._transport.request_json(
            "/sandbox/exec",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxProcessResult(**payload["result"])

    async def start(
        self, input: Union[SandboxExecParams, Dict[str, object]]
    ) -> SandboxProcessHandle:
        params = input if isinstance(input, SandboxExecParams) else SandboxExecParams(**input)
        payload = await self._transport.request_json(
            "/sandbox/processes",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxProcessHandle(
            self._transport,
            SandboxProcessSummary(**payload["process"]),
        )

    async def get(self, process_id: str) -> SandboxProcessHandle:
        payload = await self._transport.request_json(f"/sandbox/processes/{process_id}")
        return SandboxProcessHandle(
            self._transport,
            SandboxProcessSummary(**payload["process"]),
        )

    async def list(
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

        payload = await self._transport.request_json(
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
    def __init__(
        self,
        transport: RuntimeTransport,
        get_connection_info,
        status,
        runtime_proxy_override: Optional[str] = None,
    ):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._status = status
        self._runtime_proxy_override = runtime_proxy_override

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

    async def refresh(self, include_events: bool = False) -> "SandboxFileWatchHandle":
        params = {"includeEvents": True} if include_events else None
        payload = await self._transport.request_json(
            f"/sandbox/files/watch/{self.id}",
            params=params,
        )
        self._status = SandboxFileWatchStatus(**payload["watch"])
        return self

    async def stop(self) -> None:
        await self._transport.request_json(
            f"/sandbox/files/watch/{self.id}",
            method="DELETE",
        )
        self._status = self._status.model_copy(
            update={
                "active": False,
                "stopped_at": self._status.stopped_at or int(datetime.now().timestamp() * 1000),
            }
        )

    async def events(
        self,
        *,
        cursor: Optional[int] = None,
        route: str = "ws",
    ) -> AsyncIterator[object]:
        connection = await self._get_connection_info()
        query = urlencode(
            [
                ("sessionId", connection.sandbox_id),
                *([("cursor", str(cursor))] if cursor is not None else []),
            ]
        )
        target = to_websocket_transport_target(
            connection.base_url,
            f"/sandbox/files/watch/{self.id}/{route}?{query}",
            self._runtime_proxy_override,
        )
        headers = build_headers(connection.token, host_header=target.host_header)
        connect_kwargs = {}
        if target.connect_host is not None and target.connect_port is not None:
            sock = socket.create_connection(
                (target.connect_host, target.connect_port),
                timeout=self._transport._timeout,
            )
            sock.setblocking(False)
            connect_kwargs["sock"] = sock
        try:
            websocket = await async_ws_connect(
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
                    message = await websocket.recv()
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
            await websocket.close()


class SandboxWatchDirHandle:
    def __init__(
        self,
        watch: SandboxFileWatchHandle,
        on_event: Callable[[SandboxFileSystemEvent], object],
        *,
        on_exit: Optional[Callable[[Optional[BaseException]], object]] = None,
        timeout_ms: Optional[int] = None,
    ):
        self._watch = watch
        self._root_path = watch.current.path
        self._on_event = on_event
        self._on_exit = on_exit
        self._stop_requested = False
        self._exit_notified = False
        self._task = asyncio.create_task(self._run())
        effective_timeout = DEFAULT_WATCH_TIMEOUT_MS if timeout_ms is None else timeout_ms
        self._timeout_task = (
            asyncio.create_task(self._auto_stop(effective_timeout))
            if effective_timeout > 0
            else None
        )

    async def stop(self) -> None:
        if self._stop_requested:
            return
        self._stop_requested = True

        if self._timeout_task is not None:
            self._timeout_task.cancel()
            self._timeout_task = None

        try:
            await self._watch.stop()
        except HyperbrowserError as error:
            if error.status_code not in {404, 409}:
                raise

        if asyncio.current_task() is not self._task:
            await self._task

    async def _auto_stop(self, timeout_ms: int) -> None:
        try:
            await asyncio.sleep(timeout_ms / 1000.0)
            await self.stop()
        except asyncio.CancelledError:
            return

    async def _run(self) -> None:
        exit_error = None
        try:
            async for message in self._watch.events():
                event_type = _normalize_event_type(message.event.op)
                if not event_type:
                    continue
                result = self._on_event(
                    SandboxFileSystemEvent(
                        type=event_type,
                        name=_relative_watch_name(self._root_path, message.event.path),
                    )
                )
                if inspect.isawaitable(result):
                    await result
        except BaseException as error:
            exit_error = error
        finally:
            if self._timeout_task is not None:
                self._timeout_task.cancel()
                self._timeout_task = None
            if not self._exit_notified:
                self._exit_notified = True
                if self._on_exit is not None:
                    result = self._on_exit(exit_error)
                    if inspect.isawaitable(result):
                        await result


class SandboxFilesApi:
    def __init__(
        self,
        transport: RuntimeTransport,
        get_connection_info,
        runtime_proxy_override: Optional[str] = None,
    ):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._runtime_proxy_override = runtime_proxy_override

    async def list(
        self,
        path: str,
        *,
        depth: Optional[int] = None,
    ) -> List[SandboxFileInfo]:
        depth = 1 if depth is None else depth
        if depth < 1:
            raise ValueError("depth should be at least one")

        payload = await self._transport.request_json(
            "/sandbox/files",
            params={
                "path": path,
                "depth": depth,
            },
        )
        return [_normalize_file_info(entry) for entry in payload.get("entries", [])]

    async def get_info(self, path: str) -> SandboxFileInfo:
        payload = await self._transport.request_json(
            "/sandbox/files/stat",
            params={"path": path},
        )
        return _normalize_file_info(payload["file"])

    async def stat(self, path: str) -> SandboxFileInfo:
        return await self.get_info(path)

    async def exists(self, path: str) -> bool:
        try:
            await self.get_info(path)
            return True
        except HyperbrowserError as error:
            if error.status_code == 404:
                return False
            if "not found" in str(error).lower() or "no such file" in str(error).lower():
                return False
            raise

    async def read(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
        format: str = "text",
    ):
        if format == "text":
            return (
                await self._read_wire(
                    path,
                    offset=offset,
                    length=length,
                    encoding="utf8",
                )
            ).content

        response = await self._read_wire(
            path,
            offset=offset,
            length=length,
            encoding="base64",
        )
        content = base64.b64decode(response.content)
        if format in {"bytes", "blob"}:
            return content
        if format == "stream":
            return io.BytesIO(content)
        raise ValueError("format should be one of: text, bytes, blob, stream")

    async def read_text(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> str:
        return await self.read(path, offset=offset, length=length, format="text")

    async def read_bytes(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> bytes:
        return await self.read(path, offset=offset, length=length, format="bytes")

    async def write(
        self,
        path_or_files: Union[str, List[Union[SandboxFileWriteEntry, Dict[str, object]]]],
        data: Optional[Union[str, bytes, bytearray]] = None,
    ):
        if isinstance(path_or_files, str):
            if data is None:
                raise ValueError("Path and data are required")
            payload = await self._transport.request_json(
                "/sandbox/files/write",
                method="POST",
                json_body={
                    "path": path_or_files,
                    **_encode_write_data(data),
                },
                headers={"content-type": "application/json"},
            )
            return _normalize_write_info(payload["files"][0])

        if not path_or_files:
            return []

        encoded_files = []
        for entry in path_or_files:
            normalized = (
                entry
                if isinstance(entry, SandboxFileWriteEntry)
                else SandboxFileWriteEntry(**entry)
            )
            encoded_files.append(
                {
                    "path": normalized.path,
                    **_encode_write_data(normalized.data),
                }
            )

        payload = await self._transport.request_json(
            "/sandbox/files/write",
            method="POST",
            json_body={"files": encoded_files},
            headers={"content-type": "application/json"},
        )
        return [_normalize_write_info(entry) for entry in payload.get("files", [])]

    async def write_text(
        self,
        path: str,
        data: str,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
    ):
        return await self._write_single(
            path,
            data,
            append=append,
            mode=mode,
            encoding="utf8",
        )

    async def write_bytes(
        self,
        path: str,
        data: bytes,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
    ):
        return await self._write_single(
            path,
            base64.b64encode(data).decode("ascii"),
            append=append,
            mode=mode,
            encoding="base64",
        )

    async def upload(self, path: str, data: Union[str, bytes, bytearray]):
        body = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        payload = await self._transport.request_json(
            "/sandbox/files/upload",
            method="PUT",
            params={"path": path},
            content=body,
        )
        return SandboxFileTransferResult(**payload)

    async def download(self, path: str) -> bytes:
        return await self._transport.request_bytes(
            "/sandbox/files/download",
            params={"path": path},
        )

    async def make_dir(
        self,
        path: str,
        *,
        parents: Optional[bool] = None,
        mode: Optional[str] = None,
    ) -> bool:
        payload = await self._transport.request_json(
            "/sandbox/files/mkdir",
            method="POST",
            json_body={
                "path": path,
                "parents": parents,
                "mode": mode,
            },
            headers={"content-type": "application/json"},
        )
        return bool(payload.get("created"))

    async def mkdir(
        self,
        path: str,
        *,
        parents: Optional[bool] = None,
        mode: Optional[str] = None,
    ) -> bool:
        return await self.make_dir(path, parents=parents, mode=mode)

    async def rename(self, old_path: str, new_path: str) -> SandboxFileInfo:
        payload = await self._transport.request_json(
            "/sandbox/files/move",
            method="POST",
            json_body={
                "from": old_path,
                "to": new_path,
            },
            headers={"content-type": "application/json"},
        )
        return _normalize_file_info(payload["entry"])

    async def move(
        self,
        *,
        source: str,
        destination: str,
        overwrite: Optional[bool] = None,
    ) -> SandboxFileInfo:
        return await self.rename(source, destination)

    async def remove(self, path: str, *, recursive: Optional[bool] = None) -> None:
        await self._transport.request_json(
            "/sandbox/files/delete",
            method="POST",
            json_body=SandboxFileDeleteParams(
                path=path,
                recursive=recursive,
            ).model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )

    async def delete(self, path: str, *, recursive: Optional[bool] = None) -> None:
        await self.remove(path, recursive=recursive)

    async def copy(
        self,
        params: Optional[Union[SandboxFileCopyParams, Dict[str, object]]] = None,
        *,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        recursive: Optional[bool] = None,
        overwrite: Optional[bool] = None,
    ) -> SandboxFileInfo:
        if params is None:
            normalized = SandboxFileCopyParams(
                source=source,
                destination=destination,
                recursive=recursive,
                overwrite=overwrite,
            )
        elif isinstance(params, SandboxFileCopyParams):
            normalized = params
        else:
            normalized = SandboxFileCopyParams(**params)

        payload = await self._transport.request_json(
            "/sandbox/files/copy",
            method="POST",
            json_body={
                "from": normalized.source,
                "to": normalized.destination,
                "recursive": normalized.recursive,
                "overwrite": normalized.overwrite,
            },
            headers={"content-type": "application/json"},
        )
        return _normalize_file_info(payload["entry"])

    async def chmod(
        self,
        params: Optional[Union[SandboxFileChmodParams, Dict[str, object]]] = None,
        *,
        path: Optional[str] = None,
        mode: Optional[str] = None,
        recursive: Optional[bool] = None,
    ) -> None:
        normalized = (
            params
            if isinstance(params, SandboxFileChmodParams)
            else SandboxFileChmodParams(
                **(params or {"path": path, "mode": mode, "recursive": recursive})
            )
        )
        await self._transport.request_json(
            "/sandbox/files/chmod",
            method="POST",
            json_body=normalized.model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )

    async def chown(
        self,
        params: Optional[Union[SandboxFileChownParams, Dict[str, object]]] = None,
        *,
        path: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        recursive: Optional[bool] = None,
    ) -> None:
        normalized = (
            params
            if isinstance(params, SandboxFileChownParams)
            else SandboxFileChownParams(
                **(
                    params
                    or {
                        "path": path,
                        "uid": uid,
                        "gid": gid,
                        "recursive": recursive,
                    }
                )
            )
        )
        await self._transport.request_json(
            "/sandbox/files/chown",
            method="POST",
            json_body=normalized.model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )

    async def watch(self, path: str, *, recursive: Optional[bool] = None):
        payload = await self._transport.request_json(
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
            self._runtime_proxy_override,
        )

    async def watch_dir(
        self,
        path: str,
        on_event: Callable[[SandboxFileSystemEvent], object],
        *,
        recursive: Optional[bool] = None,
        timeout_ms: Optional[int] = None,
        on_exit: Optional[Callable[[Optional[BaseException]], object]] = None,
    ) -> SandboxWatchDirHandle:
        return SandboxWatchDirHandle(
            await self.watch(path, recursive=recursive),
            on_event,
            on_exit=on_exit,
            timeout_ms=timeout_ms,
        )

    async def get_watch(
        self, watch_id: str, include_events: bool = False
    ) -> SandboxFileWatchHandle:
        payload = await self._transport.request_json(
            f"/sandbox/files/watch/{watch_id}",
            params={"includeEvents": True} if include_events else None,
        )
        return SandboxFileWatchHandle(
            self._transport,
            self._get_connection_info,
            SandboxFileWatchStatus(**payload["watch"]),
            self._runtime_proxy_override,
        )

    async def upload_url(
        self,
        path: str,
        *,
        expires_in_seconds: Optional[int] = None,
        one_time: Optional[bool] = None,
    ) -> SandboxPresignedUrl:
        payload = await self._transport.request_json(
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

    async def download_url(
        self,
        path: str,
        *,
        expires_in_seconds: Optional[int] = None,
        one_time: Optional[bool] = None,
    ) -> SandboxPresignedUrl:
        payload = await self._transport.request_json(
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

    async def _read_wire(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
        encoding: str,
    ) -> SandboxFileReadResult:
        payload = await self._transport.request_json(
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

    async def _write_single(
        self,
        path: str,
        data: str,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
        encoding: str,
    ):
        payload = await self._transport.request_json(
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
        return _normalize_write_info(payload["files"][0])


class SandboxTerminalConnection:
    def __init__(self, websocket):
        self._websocket = websocket

    async def events(self) -> AsyncIterator[object]:
        while True:
            try:
                message = await self._websocket.recv()
            except ConnectionClosed:
                break

            if isinstance(message, bytes):
                message = message.decode("utf-8")
            parsed = json.loads(message)
            if parsed["type"] == "output":
                normalized = _normalize_terminal_output_chunk(parsed)
                yield SandboxTerminalOutputEvent(
                    type="output",
                    **normalized,
                )
            elif parsed["type"] == "exit":
                yield SandboxTerminalExitEvent(
                    type="exit",
                    status=_normalize_terminal_status(parsed["status"]),
                )

    async def write(self, data: Union[str, bytes, bytearray]) -> None:
        payload = {
            "type": "input",
            "data": data if isinstance(data, str) else base64.b64encode(bytes(data)).decode("ascii"),
        }
        if not isinstance(data, str):
            payload["encoding"] = "base64"
        await self._websocket.send(json.dumps(payload))

    async def resize(self, rows: int, cols: int) -> None:
        await self._websocket.send(
            json.dumps(
                {
                    "type": "resize",
                    "rows": rows,
                    "cols": cols,
                }
            )
        )

    async def close(self) -> None:
        await self._websocket.close()


class SandboxTerminalHandle:
    def __init__(
        self,
        transport: RuntimeTransport,
        get_connection_info,
        status,
        runtime_proxy_override: Optional[str] = None,
    ):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._status = status
        self._runtime_proxy_override = runtime_proxy_override

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

    async def refresh(self, include_output: bool = False) -> "SandboxTerminalHandle":
        payload = await self._transport.request_json(
            f"/sandbox/pty/{self.id}",
            params={"includeOutput": True} if include_output else None,
        )
        self._status = _normalize_terminal_status(payload["pty"])
        return self

    async def wait(
        self,
        timeout_ms: Optional[int] = None,
        include_output: Optional[bool] = None,
    ) -> SandboxTerminalStatus:
        payload = await self._transport.request_json(
            f"/sandbox/pty/{self.id}/wait",
            method="POST",
            json_body=SandboxTerminalWaitParams(
                timeout_ms=timeout_ms,
                include_output=include_output,
            ).model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        self._status = _normalize_terminal_status(payload["pty"])
        return self.current

    async def signal(self, signal: Optional[str] = None) -> SandboxTerminalStatus:
        payload = await self._transport.request_json(
            f"/sandbox/pty/{self.id}/kill",
            method="POST",
            json_body={"signal": signal},
            headers={"content-type": "application/json"},
        )
        self._status = _normalize_terminal_status(payload["pty"])
        return self.current

    async def kill(
        self,
        signal: Optional[str] = None,
        *,
        timeout_ms: Optional[int] = None,
    ) -> SandboxTerminalStatus:
        await self.signal(signal)
        if timeout_ms is None:
            timeout_ms = int(DEFAULT_TERMINAL_KILL_WAIT_SECONDS * 1000)
        return await self.wait(timeout_ms=timeout_ms)

    async def resize(self, rows: int, cols: int) -> SandboxTerminalStatus:
        payload = await self._transport.request_json(
            f"/sandbox/pty/{self.id}/resize",
            method="POST",
            json_body={"rows": rows, "cols": cols},
            headers={"content-type": "application/json"},
        )
        self._status = _normalize_terminal_status(payload["pty"])
        return self.current

    async def attach(self) -> SandboxTerminalConnection:
        connection = await self._get_connection_info()
        target = to_websocket_transport_target(
            connection.base_url,
            f"/sandbox/pty/{self.id}/ws?sessionId={connection.sandbox_id}",
            self._runtime_proxy_override,
        )
        headers = build_headers(connection.token, host_header=target.host_header)
        connect_kwargs = {}
        if target.connect_host is not None and target.connect_port is not None:
            sock = socket.create_connection(
                (target.connect_host, target.connect_port),
                timeout=self._transport._timeout,
            )
            sock.setblocking(False)
            connect_kwargs["sock"] = sock

        try:
            websocket = await async_ws_connect(
                target.url,
                additional_headers=headers,
                open_timeout=self._transport._timeout,
                **connect_kwargs,
            )
        except BaseException as error:
            raise _normalize_websocket_error(error)

        return SandboxTerminalConnection(websocket)


class SandboxTerminalApi:
    def __init__(
        self,
        transport: RuntimeTransport,
        get_connection_info,
        runtime_proxy_override: Optional[str] = None,
    ):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._runtime_proxy_override = runtime_proxy_override

    async def create(
        self,
        input: Union[SandboxTerminalCreateParams, Dict[str, object]],
    ) -> SandboxTerminalHandle:
        params = (
            input
            if isinstance(input, SandboxTerminalCreateParams)
            else SandboxTerminalCreateParams(**input)
        )
        payload = await self._transport.request_json(
            "/sandbox/pty",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxTerminalHandle(
            self._transport,
            self._get_connection_info,
            _normalize_terminal_status(payload["pty"]),
            self._runtime_proxy_override,
        )

    async def get(
        self, terminal_id: str, include_output: bool = False
    ) -> SandboxTerminalHandle:
        payload = await self._transport.request_json(
            f"/sandbox/pty/{terminal_id}",
            params={"includeOutput": True} if include_output else None,
        )
        return SandboxTerminalHandle(
            self._transport,
            self._get_connection_info,
            _normalize_terminal_status(payload["pty"]),
            self._runtime_proxy_override,
        )


class SandboxHandle:
    def __init__(self, service: "SandboxManager", detail: SandboxDetail):
        self._service = service
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)
        self._transport = RuntimeTransport(
            self._resolve_runtime_connection,
            service.runtime_timeout,
            service.runtime_proxy_override,
        )
        self.processes = SandboxProcessesApi(self._transport)
        self.files = SandboxFilesApi(
            self._transport,
            self._resolve_runtime_socket_info,
            service.runtime_proxy_override,
        )
        self.terminal = SandboxTerminalApi(
            self._transport,
            self._resolve_runtime_socket_info,
            service.runtime_proxy_override,
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

    async def info(self) -> SandboxDetail:
        detail = await self._service.get_detail(self.id)
        self._hydrate(detail)
        return _copy_model(self._detail)

    async def refresh(self) -> "SandboxHandle":
        await self.info()
        return self

    async def connect(self) -> "SandboxHandle":
        await self.create_runtime_session(force_refresh=True)
        return self

    async def stop(self) -> BasicResponse:
        response = await self._service.stop(self.id)
        self._clear_runtime_session("closed")
        return response

    async def create_memory_snapshot(
        self, params: Optional[Union[SandboxMemorySnapshotParams, Dict[str, object]]] = None
    ) -> SandboxMemorySnapshotResult:
        normalized = (
            params
            if isinstance(params, SandboxMemorySnapshotParams)
            else SandboxMemorySnapshotParams(**(params or {}))
        )
        return await self._service.create_memory_snapshot(self.id, normalized)

    async def expose(
        self, params: Union[SandboxExposeParams, Dict[str, object]]
    ) -> SandboxExposeResult:
        normalized = (
            params
            if isinstance(params, SandboxExposeParams)
            else SandboxExposeParams(**params)
        )
        return await self._service.expose(self.id, normalized, runtime=self.runtime)

    def get_exposed_url(self, port: int) -> str:
        return _build_sandbox_exposed_url(self.runtime, port)

    async def create_runtime_session(
        self, force_refresh: bool = False
    ) -> SandboxRuntimeSession:
        self._assert_runtime_available()
        if (
            not force_refresh
            and self._runtime_session is not None
            and not _expires_within_buffer(self._runtime_session.token_expires_at)
        ):
            return _copy_model(self._runtime_session)

        detail = await self._service.get_detail(self.id)
        self._hydrate(detail)
        if self._runtime_session is None:
            raise HyperbrowserError(
                f"Sandbox {self.id} is not running",
                status_code=409,
                code="sandbox_not_running",
                retryable=False,
                service="runtime",
            )
        return _copy_model(self._runtime_session)

    async def exec(self, input: Union[str, SandboxExecParams, Dict[str, object]]):
        if isinstance(input, str):
            params = SandboxExecParams(command=input)
        elif isinstance(input, SandboxExecParams):
            params = input
        else:
            params = SandboxExecParams(**input)
        return await self.processes.exec(params)

    async def get_process(self, process_id: str) -> SandboxProcessHandle:
        return await self.processes.get(process_id)

    def _hydrate(self, detail: SandboxDetail) -> None:
        self._detail = detail
        self._runtime_session = self._to_runtime_session(detail)

    async def _resolve_runtime_connection(
        self, force_refresh: bool = False
    ) -> RuntimeConnection:
        session = await self.create_runtime_session(force_refresh=force_refresh)
        return RuntimeConnection(
            sandbox_id=self.id,
            base_url=session.runtime.base_url,
            token=session.token,
        )

    async def _resolve_runtime_socket_info(self) -> RuntimeConnection:
        session = await self.create_runtime_session()
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
        self.runtime_proxy_override = getattr(
            client.config,
            "runtime_proxy_override",
            None,
        )

    async def create(
        self, params: Union[CreateSandboxParams, Dict[str, object]]
    ) -> SandboxHandle:
        normalized = (
            params if isinstance(params, CreateSandboxParams) else CreateSandboxParams(**params)
        )
        detail = await self._create_detail(normalized)
        return self.attach(detail)

    async def start_from_snapshot(
        self, params: Union[StartSandboxFromSnapshotParams, Dict[str, object]]
    ) -> SandboxHandle:
        return await self.create(params)

    async def get(self, sandbox_id: str) -> SandboxHandle:
        return self.attach(await self.get_detail(sandbox_id))

    async def connect(self, sandbox_id: str) -> SandboxHandle:
        sandbox = await self.get(sandbox_id)
        await sandbox.connect()
        return sandbox

    async def stop(self, sandbox_id: str) -> BasicResponse:
        payload = await self._request("PUT", f"/sandbox/{sandbox_id}/stop")
        return BasicResponse(**payload)

    async def get_runtime_session(self, sandbox_id: str) -> SandboxRuntimeSession:
        detail = await self.get_detail(sandbox_id)
        session = SandboxHandle._to_runtime_session(detail)
        if session is None:
            raise HyperbrowserError(
                f"Sandbox {sandbox_id} is not running",
                status_code=409,
                code="sandbox_not_running",
                retryable=False,
                service="runtime",
            )
        return session

    async def get_detail(self, sandbox_id: str) -> SandboxDetail:
        payload = await self._request("GET", f"/sandbox/{sandbox_id}")
        return SandboxDetail(**payload)

    def attach(self, detail: SandboxDetail) -> SandboxHandle:
        return SandboxHandle(self, detail)

    async def create_memory_snapshot(
        self,
        sandbox_id: str,
        params: Optional[SandboxMemorySnapshotParams] = None,
    ) -> SandboxMemorySnapshotResult:
        payload = await self._request(
            "POST",
            f"/sandbox/{sandbox_id}/snapshot",
            data=(params or SandboxMemorySnapshotParams()).model_dump(
                exclude_none=True, by_alias=True
            ),
        )
        return SandboxMemorySnapshotResult(**payload)

    async def expose(
        self,
        sandbox_id: str,
        params: SandboxExposeParams,
        *,
        runtime=None,
    ) -> SandboxExposeResult:
        payload = await self._request(
            "POST",
            f"/sandbox/{sandbox_id}/expose",
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        target_runtime = runtime or (await self.get_detail(sandbox_id)).runtime
        return SandboxExposeResult(
            port=payload["port"],
            auth=payload["auth"],
            url=_build_sandbox_exposed_url(target_runtime, payload["port"]),
        )

    async def _create_detail(self, params: CreateSandboxParams) -> SandboxDetail:
        payload = await self._request(
            "POST",
            "/sandbox",
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return SandboxDetail(**payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        data: Optional[Dict[str, object]] = None,
    ):
        try:
            response = await self._client.transport.client.request(
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
