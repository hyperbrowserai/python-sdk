import pytest

from hyperbrowser.models import SandboxExecParams

from tests.helpers.config import create_async_client
from tests.helpers.errors import expect_hyperbrowser_error_async
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_runtime_ready_async,
)


async def _collect_process_stream(events):
    output = []
    async for event in events:
        output.append(event)
        if event.type == "exit":
            break
    return output


@pytest.mark.anyio
async def test_async_sandbox_process_e2e():
    client = create_async_client()
    sandbox = None

    try:
        sandbox = await client.sandboxes.create(
            default_sandbox_params("py-async-process")
        )
        await wait_for_runtime_ready_async(sandbox)

        result = await sandbox.exec("echo process-exec-ok")
        assert result.exit_code == 0
        assert "process-exec-ok" in result.stdout

        result = await sandbox.exec(
            SandboxExecParams(
                command="bash",
                args=["-lc", "echo process-exec-fail 1>&2; exit 7"],
            )
        )
        assert result.exit_code == 7
        assert "process-exec-fail" in result.stderr

        stdin_process = await sandbox.processes.start(
            SandboxExecParams(
                command="bash",
                args=["-lc", "read line; echo stdout:$line; echo stderr:$line 1>&2"],
            )
        )
        fetched = await sandbox.get_process(stdin_process.id)
        assert fetched.id == stdin_process.id

        listing = await sandbox.processes.list(limit=20)
        assert any(entry.id == stdin_process.id for entry in listing.data)

        await stdin_process.write_stdin("sdk-stdin\n", eof=True)
        result = await stdin_process.wait()
        assert result.exit_code == 0
        assert "stdout:sdk-stdin" in result.stdout
        assert "stderr:sdk-stdin" in result.stderr

        running_process = await sandbox.processes.start(
            SandboxExecParams(command="bash", args=["-lc", "sleep 30"])
        )
        refreshed = await running_process.refresh()
        assert refreshed.status in {"queued", "running"}
        result = await running_process.kill()
        assert result.status not in {"queued", "running"}

        streamed = await sandbox.processes.start(
            SandboxExecParams(
                command="bash",
                args=["-lc", "echo stream-out; echo stream-err 1>&2"],
            )
        )
        events = await _collect_process_stream(streamed.stream())
        assert any(
            event.type == "stdout" and "stream-out" in event.data for event in events
        )
        assert any(
            event.type == "stderr" and "stream-err" in event.data for event in events
        )
        assert any(event.type == "exit" for event in events)

        result_process = await sandbox.processes.start(
            SandboxExecParams(command="bash", args=["-lc", "echo result-alias-ok"])
        )
        result = await result_process.result()
        assert result.exit_code == 0
        assert "result-alias-ok" in result.stdout

        noisy_process = await sandbox.processes.start(
            SandboxExecParams(
                command="bash",
                args=[
                    "-lc",
                    'yes "process-replay-window-overflow-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" | head -n 120000',
                ],
            )
        )
        result = await noisy_process.result()
        assert len(result.stdout) > 3 * 1024 * 1024

        await expect_hyperbrowser_error_async(
            "process replay window expired",
            lambda: _collect_process_stream(noisy_process.stream(1)),
            status_code=410,
            code="replay_window_expired",
            service="runtime",
            retryable=False,
            message_includes="Replay window expired",
        )

        timeout_process = await sandbox.processes.start(
            SandboxExecParams(command="bash", args=["-lc", "sleep 10"])
        )
        await expect_hyperbrowser_error_async(
            "process wait timeout",
            lambda: timeout_process.wait(timeout_ms=100),
            status_code=408,
            service="runtime",
            retryable=False,
            message_includes="timed out",
        )
        await timeout_process.signal("TERM")
        result = await timeout_process.wait(timeout_ms=3000)
        assert result.status in {"exited", "failed", "killed", "timed_out"}

        kill_process = await sandbox.processes.start(
            SandboxExecParams(command="bash", args=["-lc", "sleep 30"])
        )
        result = await kill_process.kill()
        assert result.status not in {"queued", "running"}
        assert kill_process.status not in {"queued", "running"}

        await expect_hyperbrowser_error_async(
            "missing process get",
            lambda: sandbox.get_process("proc_missing"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes="not found",
        )
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await client.close()
