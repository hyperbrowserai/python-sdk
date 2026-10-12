import asyncio
import base64
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Union

from ...._request import coerce_request
from .....models.sandbox import (
    SandboxExecParams,
    SandboxProcessExitEvent,
    SandboxProcessListResponse,
    SandboxProcessOutputEvent,
    SandboxProcessResult,
    SandboxProcessStdinParams,
    SandboxProcessSummary,
)
from .....exceptions import HyperbrowserError
from .....models.secret import SandboxResolvedSecret
from .....secrets_common import (
    SecretProcessWait,
    SecretProcessWaitContext,
    secret_process_failed_error,
    secret_process_id,
)
from .....types import (
    SandboxExecParams as SandboxExecParamsDict,
    SandboxProcessStdinParams as SandboxProcessStdinParamsDict,
)
from ...sandboxes.shared import (
    SecretReferences,
    _normalize_exec_params,
    _runtime_process_payload,
    _secret_process_payload,
)
from ...sandboxes.process_output import (
    DEFAULT_MAX_PROCESS_OUTPUT_BYTES,
    ProcessOutput,
    validate_output_limit,
)
from .sandbox_transport import RuntimeTransport

DEFAULT_PROCESS_KILL_WAIT_SECONDS = 5.0


class SandboxProcessHandle:
    def __init__(
        self,
        transport: RuntimeTransport,
        summary: SandboxProcessSummary,
        secret_wait_context: Optional[SecretProcessWaitContext] = None,
    ):
        self._transport = transport
        self._summary = summary
        self._secret_wait_context = secret_wait_context
        self._output = None
        self._collector = None
        self._events = None
        self._changed = asyncio.Event()
        # The secret versions this process received, when it was started
        # with secrets; None otherwise.
        self.secrets: Optional[List[SandboxResolvedSecret]] = None

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
        if self._collector is not None:
            timeout = None
            if timeout_sec is not None and timeout_sec > 0:
                timeout = timeout_sec
            elif timeout_ms is not None and timeout_ms > 0:
                timeout = timeout_ms / 1000
            if not self._collector.done():
                await asyncio.wait_for(asyncio.shield(self._collector), timeout)
            return self._collected_result()
        if self._secret_wait_context is not None:
            return await self._wait_with_secrets(timeout_ms, timeout_sec)
        return await self._wait_once(timeout_ms, timeout_sec)

    async def _wait_with_secrets(
        self, timeout_ms: Optional[int], timeout_sec: Optional[int]
    ) -> SandboxProcessResult:
        context = self._secret_wait_context
        assert context is not None
        wait = SecretProcessWait(
            context, timeout_ms, timeout_sec, timeout_error=asyncio.TimeoutError
        )
        while True:
            chunk_ms, request_timeout, remaining = wait.request_budget()
            started_at = time.monotonic()
            try:
                request = self._wait_once(chunk_ms, None, request_timeout)
                result = await asyncio.wait_for(request, remaining)
                wait.remaining()
                return result
            except (TimeoutError, asyncio.TimeoutError) as error:
                if wait.deadline is not None:
                    raise asyncio.TimeoutError(
                        "Timed out waiting for command output"
                    ) from error
                raise secret_process_failed_error(
                    context.sandbox_id, self.id, "waiting for its result", error
                )
            except Exception as error:
                # An explicit local deadline keeps TimeoutError semantics. It
                # ends only this wait; callers can wait again on the handle.
                wait.remaining()
                if not isinstance(error, HyperbrowserError) or error.status_code != 408:
                    raise secret_process_failed_error(
                        context.sandbox_id, self.id, "waiting for its result", error
                    )
            await asyncio.sleep(wait.retry_delay(started_at))

    async def _wait_once(
        self,
        timeout_ms: Optional[int],
        timeout_sec: Optional[int],
        request_timeout: Optional[float] = None,
    ) -> SandboxProcessResult:
        request_options: Dict[str, Any] = {}
        if request_timeout is not None:
            request_options["request_timeout"] = request_timeout
        payload = await self._transport.request_json(
            f"/sandbox/processes/{self.id}/wait",
            method="POST",
            json_body={
                "timeoutMs": timeout_ms,
                "timeout_sec": timeout_sec,
            },
            headers={"content-type": "application/json"},
            **request_options,
        )
        result = SandboxProcessResult(**payload["result"])
        if result.output_truncated:
            raise ProcessOutput(self.id, 0).failure(
                "Retained process output is incomplete; collect output from process start"
            )
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
        data: Optional[
            Union[
                SandboxProcessStdinParamsDict,
                SandboxProcessStdinParams,
                str,
                bytes,
                bytearray,
            ]
        ] = None,
        *,
        encoding: Optional[str] = None,
        eof: Optional[bool] = None,
    ) -> None:
        if data is None or isinstance(data, (str, bytes, bytearray)):
            params = SandboxProcessStdinParams(data=data, encoding=encoding, eof=eof)
        else:
            params = coerce_request(data, SandboxProcessStdinParams, name="data")

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
        if self._output is not None:
            index = 0
            while True:
                self._changed.clear()
                while index < len(self._output.events):
                    event = self._output.events[index]
                    index += 1
                    if from_seq is None or event.seq >= from_seq:
                        yield event
                if self._collector.done():
                    yield SandboxProcessExitEvent(
                        type="exit", result=self._collected_result()
                    )
                    return
                await self._changed.wait()
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

    def _collected_result(self) -> SandboxProcessResult:
        if self._output.error is not None:
            raise self._output.error
        if self._output.result is None:
            raise self._output.failure(
                "Command stream ended before its completion event"
            )
        result = self._output.result
        self._summary = self._summary.model_copy(
            update={
                "status": result.status,
                "exit_code": result.exit_code,
                "completed_at": result.completed_at,
            }
        )
        return result

    async def _collect(self) -> None:
        try:
            async for event in self._events:
                self._output.consume(event)
                self._changed.set()
                if self._output.result is not None:
                    return
            self._output.error = self._output.failure(
                "Command stream ended before its completion event"
            )
        except asyncio.CancelledError:
            if self._output.result is None:
                self._output.error = self._output.failure(
                    "Command output collection disconnected"
                )
        except Exception as error:
            self._output.error = (
                self._output.failure(str(error))
                if not hasattr(error, "code")
                else error
            )
        finally:
            try:
                await self._events.aclose()
            except Exception as error:
                if self._output.result is None and self._output.error is None:
                    self._output.error = self._output.failure(str(error))
            finally:
                self._changed.set()

    async def disconnect(self) -> None:
        """Stop collecting output; the detached command continues running."""
        if self._collector is not None and not self._collector.done():
            if self._output.result is None and self._output.error is None:
                self._output.error = self._output.failure(
                    "Command output collection disconnected"
                )
            self._collector.cancel()
            try:
                await self._collector
            except asyncio.CancelledError:
                pass
            finally:
                # Cancellation may happen before the collector gets its first turn.
                await self._events.aclose()
                self._changed.set()

    async def result(self) -> SandboxProcessResult:
        return await self.wait()


class SandboxProcessesApi:
    def __init__(
        self,
        transport: RuntimeTransport,
        start_secret_process: Optional[
            Callable[[Dict[str, object]], Awaitable[dict]]
        ] = None,
        sandbox_id: Optional[str] = None,
    ):
        self._transport = transport
        self._start_secret_process = start_secret_process
        self._sandbox_id = sandbox_id

    async def exec(
        self,
        input: Union[SandboxExecParamsDict, SandboxExecParams, str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        run_as: Optional[str] = None,
        max_output_bytes: int = DEFAULT_MAX_PROCESS_OUTPUT_BYTES,
        secrets: Optional[SecretReferences] = None,
    ) -> SandboxProcessResult:
        handle = await self.start(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
            max_output_bytes=max_output_bytes,
            secrets=secrets,
        )
        if handle.secrets is not None:
            return await self._finish_secret_exec(handle)
        try:
            return await handle.wait()
        finally:
            await handle.disconnect()

    async def start(
        self,
        input: Union[SandboxExecParamsDict, SandboxExecParams, str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        run_as: Optional[str] = None,
        max_output_bytes: int = DEFAULT_MAX_PROCESS_OUTPUT_BYTES,
        secrets: Optional[SecretReferences] = None,
    ) -> SandboxProcessHandle:
        """Start a process.

        With ``secrets``, the start goes through the control API, which has the
        platform decrypt them into the process environment; output is then
        read with ``wait()`` rather than collected from the start.
        """
        validate_output_limit(max_output_bytes)
        params = _normalize_exec_params(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
            secrets=secrets,
        )
        if params.secrets:
            return await self._start_with_secrets(params)
        events = self._transport.stream_sse(
            "/sandbox/processes",
            method="POST",
            json_body=_runtime_process_payload(params),
        )
        try:
            started = await events.__anext__()
            if started["event"] != "started":
                raise RuntimeError("Expected process start event")
            handle = SandboxProcessHandle(
                self._transport, SandboxProcessSummary(**started["data"])
            )
        except BaseException:
            await events.aclose()
            raise
        handle._events = events
        handle._output = ProcessOutput(handle.id, max_output_bytes)
        handle._collector = asyncio.create_task(handle._collect())
        return handle

    async def _start_with_secrets(
        self, params: SandboxExecParams
    ) -> SandboxProcessHandle:
        if self._start_secret_process is None:
            raise HyperbrowserError(
                "Starting a process with secrets needs a sandbox handle; use "
                "client.sandboxes.get() and its processes API",
                code="secrets_unsupported",
            )
        payload = await self._start_secret_process(_secret_process_payload(params))
        process_id = secret_process_id(payload["process"])
        try:
            handle = SandboxProcessHandle(
                self._transport,
                SandboxProcessSummary(**dict(payload["process"], id=process_id)),
                SecretProcessWaitContext(
                    self._sandbox_id or "", getattr(self._transport, "_timeout", None)
                ),
            )
            handle.secrets = [
                SandboxResolvedSecret(**entry) for entry in payload.get("secrets") or []
            ]
            return handle
        except Exception as error:
            raise secret_process_failed_error(
                self._sandbox_id or "", process_id, "reading its start response", error
            )

    async def _finish_secret_exec(
        self, handle: SandboxProcessHandle
    ) -> SandboxProcessResult:
        """Close stdin and wait for the result, as one-shot exec does.

        The process may still be running with its secrets after a failure here,
        so failures name it instead of looking like a safe retry.
        """
        sandbox_id = self._sandbox_id or ""
        try:
            await handle.write_stdin(eof=True)
        except HyperbrowserError as error:
            # 409: the command already exited, like a pipe whose reader quit
            # early. Its result is still reported.
            if error.status_code != 409:
                raise secret_process_failed_error(
                    sandbox_id, handle.id, "closing its stdin", error
                )
        except Exception as error:
            raise secret_process_failed_error(
                sandbox_id, handle.id, "closing its stdin", error
            )
        return await handle.wait()

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
