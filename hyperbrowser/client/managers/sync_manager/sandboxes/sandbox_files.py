import base64
import io
import json
import socket
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect as sync_ws_connect

from .....exceptions import HyperbrowserError
from .....models.sandbox import (
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
    SandboxPresignFileParams,
    SandboxPresignedUrl,
)
from .....sandbox_common import build_headers, to_websocket_transport_target
from ...sandboxes.shared import (
    DEFAULT_WATCH_TIMEOUT_MS,
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
                "stopped_at": self._status.stopped_at
                or int(datetime.now().timestamp() * 1000),
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
            self._runtime_proxy_override,
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
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._timer = None
        self._stopped = threading.Event()
        self._exit_notified = False

        effective_timeout = (
            DEFAULT_WATCH_TIMEOUT_MS if timeout_ms is None else timeout_ms
        )
        if effective_timeout > 0:
            self._timer = threading.Timer(effective_timeout / 1000.0, self.stop)
            self._timer.daemon = True
            self._timer.start()

        self._thread.start()

    def stop(self) -> None:
        if self._stopped.is_set():
            return
        self._stopped.set()

        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        try:
            self._watch.stop()
        except HyperbrowserError as error:
            if error.status_code not in {404, 409}:
                raise

        if threading.current_thread() is not self._thread:
            self._thread.join()

    def _run(self) -> None:
        exit_error = None
        try:
            for message in self._watch.events():
                event_type = _normalize_event_type(message.event.op)
                if not event_type:
                    continue
                self._on_event(
                    SandboxFileSystemEvent(
                        type=event_type,
                        name=_relative_watch_name(self._root_path, message.event.path),
                    )
                )
        except BaseException as error:
            exit_error = error
        finally:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if not self._exit_notified:
                self._exit_notified = True
                if self._on_exit is not None:
                    self._on_exit(exit_error)


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

    def exists(self, path: str) -> bool:
        try:
            self.get_info(path)
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

    def get_info(self, path: str) -> SandboxFileInfo:
        payload = self._transport.request_json(
            "/sandbox/files/stat",
            params={"path": path},
        )
        return _normalize_file_info(payload["file"])

    def stat(self, path: str) -> SandboxFileInfo:
        return self.get_info(path)

    def list(
        self,
        path: str,
        *,
        depth: Optional[int] = None,
    ) -> List[SandboxFileInfo]:
        depth = 1 if depth is None else depth
        if depth < 1:
            raise ValueError("depth should be at least one")

        payload = self._transport.request_json(
            "/sandbox/files",
            params={
                "path": path,
                "depth": depth,
            },
        )
        return [_normalize_file_info(entry) for entry in payload.get("entries", [])]

    def read(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
        format: str = "text",
    ):
        if format == "text":
            return self._read_wire(
                path, offset=offset, length=length, encoding="utf8"
            ).content

        response = self._read_wire(
            path, offset=offset, length=length, encoding="base64"
        )
        content = base64.b64decode(response.content)
        if format in {"bytes", "blob"}:
            return content
        if format == "stream":
            return io.BytesIO(content)
        raise ValueError("format should be one of: text, bytes, blob, stream")

    def read_text(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> str:
        return self.read(path, offset=offset, length=length, format="text")

    def read_bytes(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> bytes:
        return self.read(path, offset=offset, length=length, format="bytes")

    def write(
        self,
        path_or_files: Union[
            str, List[Union[SandboxFileWriteEntry, Dict[str, object]]]
        ],
        data: Optional[Union[str, bytes, bytearray]] = None,
    ):
        if isinstance(path_or_files, str):
            if data is None:
                raise ValueError("Path and data are required")
            payload = self._transport.request_json(
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

        payload = self._transport.request_json(
            "/sandbox/files/write",
            method="POST",
            json_body={"files": encoded_files},
            headers={"content-type": "application/json"},
        )
        return [_normalize_write_info(entry) for entry in payload.get("files", [])]

    def write_text(
        self,
        path: str,
        data: str,
        *,
        append: Optional[bool] = None,
        mode: Optional[str] = None,
    ):
        return self._write_single(
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
        return self._write_single(
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

    def make_dir(
        self,
        path: str,
        *,
        parents: Optional[bool] = None,
        mode: Optional[str] = None,
    ) -> bool:
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
        return bool(payload.get("created"))

    def mkdir(
        self,
        path: str,
        *,
        parents: Optional[bool] = None,
        mode: Optional[str] = None,
    ) -> bool:
        return self.make_dir(path, parents=parents, mode=mode)

    def rename(self, old_path: str, new_path: str) -> SandboxFileInfo:
        payload = self._transport.request_json(
            "/sandbox/files/move",
            method="POST",
            json_body={
                "from": old_path,
                "to": new_path,
            },
            headers={"content-type": "application/json"},
        )
        return _normalize_file_info(payload["entry"])

    def move(
        self,
        *,
        source: str,
        destination: str,
        overwrite: Optional[bool] = None,
    ) -> SandboxFileInfo:
        return self.rename(source, destination)

    def remove(self, path: str, *, recursive: Optional[bool] = None) -> None:
        self._transport.request_json(
            "/sandbox/files/delete",
            method="POST",
            json_body=SandboxFileDeleteParams(
                path=path,
                recursive=recursive,
            ).model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )

    def delete(self, path: str, *, recursive: Optional[bool] = None) -> None:
        self.remove(path, recursive=recursive)

    def copy(
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

        payload = self._transport.request_json(
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

    def chmod(
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
        self._transport.request_json(
            "/sandbox/files/chmod",
            method="POST",
            json_body=normalized.model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )

    def chown(
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
        self._transport.request_json(
            "/sandbox/files/chown",
            method="POST",
            json_body=normalized.model_dump(exclude_none=True),
            headers={"content-type": "application/json"},
        )

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
            self._runtime_proxy_override,
        )

    def watch_dir(
        self,
        path: str,
        on_event: Callable[[SandboxFileSystemEvent], object],
        *,
        recursive: Optional[bool] = None,
        timeout_ms: Optional[int] = None,
        on_exit: Optional[Callable[[Optional[BaseException]], object]] = None,
    ) -> SandboxWatchDirHandle:
        return SandboxWatchDirHandle(
            self.watch(path, recursive=recursive),
            on_event,
            on_exit=on_exit,
            timeout_ms=timeout_ms,
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
            self._runtime_proxy_override,
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

    def _read_wire(
        self,
        path: str,
        *,
        offset: Optional[int] = None,
        length: Optional[int] = None,
        encoding: str,
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

    def _write_single(
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
        return _normalize_write_info(payload["files"][0])
