import asyncio
import base64
import inspect
import io
import json
import socket
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

from websockets.asyncio.client import connect as async_ws_connect
from websockets.exceptions import ConnectionClosed

from .....exceptions import HyperbrowserError
from .....models.sandbox import (
    SandboxFileChmodParams,
    SandboxFileChownParams,
    SandboxFileCopyParams,
    SandboxFileDeleteParams,
    SandboxFileInfo,
    SandboxFileMoveParams,
    SandboxFileReadResult,
    SandboxFileSystemEvent,
    SandboxFileWriteEntry,
    SandboxFileTransferResult,
    SandboxFileWatchDoneEvent,
    SandboxFileWatchEventMessage,
    SandboxFileWatchStatus,
    SandboxPresignFileParams,
    SandboxPresignedUrl,
)
from .....sandbox_common import build_headers, to_websocket_transport_target
from ...sandboxes.shared import (
    DEFAULT_WATCH_TIMEOUT_MS,
    _encode_batch_write_entry,
    _copy_model,
    _encode_write_data,
    _normalize_event_type,
    _normalize_file_info,
    _normalize_websocket_error,
    _normalize_write_info,
    _relative_watch_name,
)
from .sandbox_transport import RuntimeTransport


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
                "stopped_at": self._status.stopped_at
                or int(datetime.now().timestamp() * 1000),
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
            connection.sandbox_id,
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
        effective_timeout = (
            DEFAULT_WATCH_TIMEOUT_MS if timeout_ms is None else timeout_ms
        )
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
        default_run_as: Optional[str] = None,
    ):
        self._transport = transport
        self._get_connection_info = get_connection_info
        self._runtime_proxy_override = runtime_proxy_override
        self._default_run_as = default_run_as.strip() if default_run_as else None

    def with_run_as(self, run_as: Optional[str]):
        normalized = run_as.strip() if run_as else None
        return SandboxFilesApi(
            self._transport,
            self._get_connection_info,
            self._runtime_proxy_override,
            default_run_as=normalized,
        )

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
            params=self._with_run_as_params(
                {
                    "path": path,
                    "depth": depth,
                }
            ),
        )
        return [_normalize_file_info(entry) for entry in payload.get("entries", [])]

    async def get_info(self, path: str) -> SandboxFileInfo:
        payload = await self._transport.request_json(
            "/sandbox/files/stat",
            params=self._with_run_as_params({"path": path}),
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
            if (
                "not found" in str(error).lower()
                or "no such file" in str(error).lower()
            ):
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
        path_or_files: Union[str, List[SandboxFileWriteEntry]],
        data: Optional[Union[str, bytes, bytearray]] = None,
    ):
        if isinstance(path_or_files, str):
            if data is None:
                raise ValueError("Path and data are required")
            payload = await self._transport.request_json(
                "/sandbox/files/write",
                method="POST",
                json_body=self._with_run_as_body(
                    {
                        "path": path_or_files,
                        **_encode_write_data(data),
                    }
                ),
                headers={"content-type": "application/json"},
            )
            return _normalize_write_info(payload["files"][0])

        if not path_or_files:
            return []

        encoded_files = []
        for entry in path_or_files:
            if not isinstance(entry, SandboxFileWriteEntry):
                raise TypeError("files must contain SandboxFileWriteEntry instances")
            encoded_files.append(_encode_batch_write_entry(entry))

        payload = await self._transport.request_json(
            "/sandbox/files/write",
            method="POST",
            json_body=self._with_run_as_body({"files": encoded_files}),
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
            params=self._with_run_as_params({"path": path}),
            content=body,
        )
        return SandboxFileTransferResult(**payload)

    async def download(self, path: str) -> bytes:
        return await self._transport.request_bytes(
            "/sandbox/files/download",
            params=self._with_run_as_params({"path": path}),
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
            json_body=self._with_run_as_body(
                {
                    "path": path,
                    "parents": parents,
                    "mode": mode,
                }
            ),
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

    async def rename(
        self,
        old_path: str,
        new_path: str,
        *,
        overwrite: Optional[bool] = None,
    ) -> SandboxFileInfo:
        payload = SandboxFileMoveParams(
            source=old_path,
            destination=new_path,
            overwrite=overwrite,
        ).model_dump(exclude_none=True)
        payload["from"] = payload.pop("source")
        payload["to"] = payload.pop("destination")
        payload = await self._transport.request_json(
            "/sandbox/files/move",
            method="POST",
            json_body=self._with_run_as_body(payload),
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
        return await self.rename(source, destination, overwrite=overwrite)

    async def remove(self, path: str, *, recursive: Optional[bool] = None) -> None:
        await self._transport.request_json(
            "/sandbox/files/delete",
            method="POST",
            json_body=self._with_run_as_body(
                SandboxFileDeleteParams(
                    path=path,
                    recursive=recursive,
                ).model_dump(exclude_none=True)
            ),
            headers={"content-type": "application/json"},
        )

    async def delete(self, path: str, *, recursive: Optional[bool] = None) -> None:
        await self.remove(path, recursive=recursive)

    async def copy(
        self,
        params: Optional[SandboxFileCopyParams] = None,
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
            raise TypeError("params must be a SandboxFileCopyParams instance")

        payload = await self._transport.request_json(
            "/sandbox/files/copy",
            method="POST",
            json_body=self._with_run_as_body(
                {
                    "from": normalized.source,
                    "to": normalized.destination,
                    "recursive": normalized.recursive,
                    "overwrite": normalized.overwrite,
                }
            ),
            headers={"content-type": "application/json"},
        )
        return _normalize_file_info(payload["entry"])

    async def chmod(
        self,
        params: Optional[SandboxFileChmodParams] = None,
        *,
        path: Optional[str] = None,
        mode: Optional[str] = None,
        recursive: Optional[bool] = None,
    ) -> None:
        if params is None:
            normalized = SandboxFileChmodParams(
                path=path,
                mode=mode,
                recursive=recursive,
            )
        elif isinstance(params, SandboxFileChmodParams):
            normalized = params
        else:
            raise TypeError("params must be a SandboxFileChmodParams instance")
        await self._transport.request_json(
            "/sandbox/files/chmod",
            method="POST",
            json_body=self._with_run_as_body(normalized.model_dump(exclude_none=True)),
            headers={"content-type": "application/json"},
        )

    async def chown(
        self,
        params: Optional[SandboxFileChownParams] = None,
        *,
        path: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        recursive: Optional[bool] = None,
    ) -> None:
        if params is None:
            normalized = SandboxFileChownParams(
                path=path,
                uid=uid,
                gid=gid,
                recursive=recursive,
            )
        elif isinstance(params, SandboxFileChownParams):
            normalized = params
        else:
            raise TypeError("params must be a SandboxFileChownParams instance")
        await self._transport.request_json(
            "/sandbox/files/chown",
            method="POST",
            json_body=self._with_run_as_body(normalized.model_dump(exclude_none=True)),
            headers={"content-type": "application/json"},
        )

    async def watch(self, path: str, *, recursive: Optional[bool] = None):
        payload = await self._transport.request_json(
            "/sandbox/files/watch",
            method="POST",
            json_body=self._with_run_as_body(
                {
                    "path": path,
                    "recursive": recursive,
                }
            ),
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
            json_body=self._with_run_as_body(
                SandboxPresignFileParams(
                    path=path,
                    expires_in_seconds=expires_in_seconds,
                    one_time=one_time,
                ).model_dump(exclude_none=True, by_alias=True)
            ),
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
            json_body=self._with_run_as_body(
                SandboxPresignFileParams(
                    path=path,
                    expires_in_seconds=expires_in_seconds,
                    one_time=one_time,
                ).model_dump(exclude_none=True, by_alias=True)
            ),
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
            json_body=self._with_run_as_body(
                {
                    "path": path,
                    "offset": offset,
                    "length": length,
                    "encoding": encoding,
                }
            ),
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
            json_body=self._with_run_as_body(
                {
                    "path": path,
                    "data": data,
                    "append": append,
                    "mode": mode,
                    "encoding": encoding,
                }
            ),
            headers={"content-type": "application/json"},
        )
        return _normalize_write_info(payload["files"][0])

    def _with_run_as_params(
        self, params: Dict[str, Union[str, int, bool, None]]
    ) -> Dict[str, Union[str, int, bool, None]]:
        if not self._default_run_as:
            return params
        enriched = dict(params)
        enriched["runAs"] = self._default_run_as
        return enriched

    def _with_run_as_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        if not self._default_run_as:
            return body
        enriched = dict(body)
        enriched["runAs"] = self._default_run_as
        return enriched
