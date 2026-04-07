import base64
from typing import AsyncIterator, Dict, Optional, Union

from .....models.sandbox import (
    SandboxExecParams,
    SandboxProcessExitEvent,
    SandboxProcessListResponse,
    SandboxProcessOutputEvent,
    SandboxProcessResult,
    SandboxProcessStdinParams,
    SandboxProcessSummary,
)
from ...sandboxes.shared import _normalize_exec_params
from .sandbox_transport import RuntimeTransport

DEFAULT_PROCESS_KILL_WAIT_SECONDS = 5.0


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
        self,
        input: Union[str, SandboxExecParams],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        run_as: Optional[str] = None,
    ) -> SandboxProcessResult:
        params = _normalize_exec_params(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
        )
        payload = await self._transport.request_json(
            "/sandbox/exec",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxProcessResult(**payload["result"])

    async def start(
        self,
        input: Union[str, SandboxExecParams],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        run_as: Optional[str] = None,
    ) -> SandboxProcessHandle:
        params = _normalize_exec_params(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
        )
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
