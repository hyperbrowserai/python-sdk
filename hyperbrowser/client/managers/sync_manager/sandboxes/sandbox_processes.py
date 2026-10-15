import base64
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Union

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
    OnePasswordSourceInput,
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
        self._changed = threading.Condition()
        self._close_stream = None
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

    def refresh(self) -> "SandboxProcessHandle":
        payload = self._transport.request_json(f"/sandbox/processes/{self.id}")
        self._summary = SandboxProcessSummary(**payload["process"])
        return self

    def wait(self, timeout_ms: Optional[int] = None, timeout_sec: Optional[int] = None):
        if self._collector is not None:
            timeout = None
            if timeout_sec is not None and timeout_sec > 0:
                timeout = timeout_sec
            elif timeout_ms is not None and timeout_ms > 0:
                timeout = timeout_ms / 1000
            with self._changed:
                ready = self._changed.wait_for(
                    lambda: self._output.result is not None
                    or self._output.error is not None,
                    timeout,
                )
                if not ready:
                    raise TimeoutError("Timed out waiting for command output")
                return self._collected_result()
        if self._secret_wait_context is not None:
            return self._wait_with_secrets(timeout_ms, timeout_sec)
        return self._wait_once(timeout_ms, timeout_sec)

    def _wait_with_secrets(
        self, timeout_ms: Optional[int], timeout_sec: Optional[int]
    ) -> SandboxProcessResult:
        context = self._secret_wait_context
        assert context is not None
        wait = SecretProcessWait(context, timeout_ms, timeout_sec)
        while True:
            chunk_ms, request_timeout, _ = wait.request_budget()
            started_at = time.monotonic()
            try:
                result = self._wait_once(chunk_ms, None, request_timeout)
                wait.remaining()
                return result
            except TimeoutError as error:
                if wait.deadline is not None:
                    raise
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
            time.sleep(wait.retry_delay(started_at))

    def _wait_once(
        self,
        timeout_ms: Optional[int],
        timeout_sec: Optional[int],
        request_timeout: Optional[float] = None,
    ) -> SandboxProcessResult:
        request_options: Dict[str, Any] = {}
        if request_timeout is not None:
            request_options["request_timeout"] = request_timeout
        payload = self._transport.request_json(
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

        self._transport.request_json(
            f"/sandbox/processes/{self.id}/stdin",
            method="POST",
            json_body=payload,
            headers={"content-type": "application/json"},
        )

    def stream(self, from_seq: Optional[int] = None):
        if self._output is not None:
            index = 0
            while True:
                with self._changed:
                    events = self._output.events[index:]
                    index += len(events)
                    done = (
                        self._output.result is not None
                        or self._output.error is not None
                    )
                    if not events and not done:
                        self._changed.wait()
                        continue
                for event in events:
                    if from_seq is None or event.seq >= from_seq:
                        yield event
                if done:
                    yield SandboxProcessExitEvent(
                        type="exit", result=self._collected_result()
                    )
                    return
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

    def _collect(self) -> None:
        try:
            for event in self._events:
                with self._changed:
                    if self._output.error is not None:
                        return
                    self._output.consume(event)
                    self._changed.notify_all()
                if self._output.result is not None:
                    return
            self._output.error = self._output.failure(
                "Command stream ended before its completion event"
            )
        except Exception as error:
            with self._changed:
                if self._output.error is None:
                    self._output.error = (
                        self._output.failure(str(error))
                        if not hasattr(error, "code")
                        else error
                    )
        finally:
            try:
                self._events.close()
            except Exception as error:
                with self._changed:
                    if self._output.result is None and self._output.error is None:
                        self._output.error = self._output.failure(str(error))
            finally:
                with self._changed:
                    self._changed.notify_all()

    def disconnect(self) -> None:
        """Stop collecting output; the detached command continues running."""
        if self._output is not None:
            with self._changed:
                if self._output.result is None and self._output.error is None:
                    self._output.error = self._output.failure(
                        "Command output collection disconnected"
                    )
                self._changed.notify_all()
            if self._close_stream is not None:
                self._close_stream()

    def result(self) -> SandboxProcessResult:
        return self.wait()


class SandboxProcessesApi:
    def __init__(
        self,
        transport: RuntimeTransport,
        start_secret_process: Optional[Callable[[Dict[str, object]], dict]] = None,
        sandbox_id: Optional[str] = None,
    ):
        self._transport = transport
        self._start_secret_process = start_secret_process
        self._sandbox_id = sandbox_id

    def exec(
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
        vault: Optional[str] = None,
        one_password: Optional[OnePasswordSourceInput] = None,
    ) -> SandboxProcessResult:
        handle = self.start(
            input,
            cwd=cwd,
            env=env,
            timeout_ms=timeout_ms,
            timeout_sec=timeout_sec,
            run_as=run_as,
            max_output_bytes=max_output_bytes,
            secrets=secrets,
            vault=vault,
            one_password=one_password,
        )
        if handle.secrets is not None:
            return self._finish_secret_exec(handle)
        try:
            return handle.wait()
        finally:
            handle.disconnect()

    def start(
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
        vault: Optional[str] = None,
        one_password: Optional[OnePasswordSourceInput] = None,
    ) -> SandboxProcessHandle:
        """Start a process.

        With ``secrets``, ``vault`` or ``one_password``, the start goes through
        the control API, which has the platform resolve them into the process
        environment; output is then read with ``wait()`` rather than collected
        from the start. ``secrets`` are merged over the vault's entries, and a
        ``one_password`` variable may not also come from ``vault``,
        ``secrets`` or ``env``.
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
            vault=vault,
            one_password=one_password,
        )
        if params.uses_secrets:
            return self._start_with_secrets(params)
        close_stream = []
        events = self._transport.stream_sse(
            "/sandbox/processes",
            method="POST",
            json_body=_runtime_process_payload(params),
            on_open=close_stream.append,
        )
        try:
            started = next(events)
            if started["event"] != "started":
                raise RuntimeError("Expected process start event")
            handle = SandboxProcessHandle(
                self._transport, SandboxProcessSummary(**started["data"])
            )
        except BaseException:
            events.close()
            raise
        handle._close_stream = close_stream[0] if close_stream else None
        handle._events = events
        handle._output = ProcessOutput(handle.id, max_output_bytes)
        handle._collector = threading.Thread(target=handle._collect, daemon=True)
        handle._collector.start()
        return handle

    def _start_with_secrets(self, params: SandboxExecParams) -> SandboxProcessHandle:
        if self._start_secret_process is None:
            raise HyperbrowserError(
                "Starting a process with secrets needs a sandbox handle; use "
                "client.sandboxes.get() and its processes API",
                code="secrets_unsupported",
            )
        payload = self._start_secret_process(_secret_process_payload(params))
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

    def _finish_secret_exec(self, handle: SandboxProcessHandle) -> SandboxProcessResult:
        """Close stdin and wait for the result, as one-shot exec does.

        The process may still be running with its secrets after a failure here,
        so failures name it instead of looking like a safe retry.
        """
        sandbox_id = self._sandbox_id or ""
        try:
            handle.write_stdin(eof=True)
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
        return handle.wait()

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
