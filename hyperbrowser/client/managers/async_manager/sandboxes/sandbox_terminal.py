import base64
import json
import socket
from typing import AsyncIterator, Dict, Optional, Union
from urllib.parse import urlencode

from websockets.asyncio.client import connect as async_ws_connect
from websockets.exceptions import ConnectionClosed

from .....models.sandbox import (
    SandboxTerminalCreateParams,
    SandboxTerminalExitEvent,
    SandboxTerminalOutputEvent,
    SandboxTerminalStatus,
    SandboxTerminalWaitParams,
)
from .....sandbox_common import build_headers, to_websocket_transport_target
from ...sandboxes.shared import (
    _copy_model,
    _normalize_terminal_output_chunk,
    _normalize_terminal_status,
    _normalize_websocket_error,
)
from .sandbox_transport import RuntimeTransport

DEFAULT_TERMINAL_KILL_WAIT_SECONDS = 5.0


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
        payload: Dict[str, object] = {
            "type": "input",
            "data": data
            if isinstance(data, str)
            else base64.b64encode(bytes(data)).decode("ascii"),
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

    async def attach(
        self,
        cursor: Optional[int] = None,
    ) -> SandboxTerminalConnection:
        connection = await self._get_connection_info()
        query = urlencode(
            [
                ("sessionId", connection.sandbox_id),
                *([("cursor", str(cursor))] if cursor is not None else []),
            ]
        )
        target = to_websocket_transport_target(
            connection.base_url,
            f"/sandbox/pty/{self.id}/ws?{query}",
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
        input: SandboxTerminalCreateParams,
    ) -> SandboxTerminalHandle:
        if not isinstance(input, SandboxTerminalCreateParams):
            raise TypeError("input must be a SandboxTerminalCreateParams instance")
        payload = await self._transport.request_json(
            "/sandbox/pty",
            method="POST",
            json_body=input.model_dump(exclude_none=True, by_alias=True),
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
