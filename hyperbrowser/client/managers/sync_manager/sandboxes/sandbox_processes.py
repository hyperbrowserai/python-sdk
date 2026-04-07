import base64
import re
from typing import Dict, Optional, Union

from .....models.sandbox import (
    SandboxExecParams,
    SandboxProcessExitEvent,
    SandboxProcessListResponse,
    SandboxProcessOutputEvent,
    SandboxProcessResult,
    SandboxProcessStdinParams,
    SandboxProcessSummary,
)
from .sandbox_transport import RuntimeTransport

DEFAULT_PROCESS_KILL_WAIT_SECONDS = 5.0
SHELL_SAFE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_@%+=:,./-]+$")


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

    def exec(
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
        payload = self._transport.request_json(
            "/sandbox/exec",
            method="POST",
            json_body=params.model_dump(exclude_none=True, by_alias=True),
            headers={"content-type": "application/json"},
        )
        return SandboxProcessResult(**payload["result"])

    def start(
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
