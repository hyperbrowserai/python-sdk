from tests.helpers.config import create_client
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()


def _collect_process_stream(events):
    output = []
    for event in events:
        output.append(event)
        if event.type == "exit":
            break
    return output


def test_sandbox_process_e2e():
    sandbox = None

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-process"))
        wait_for_runtime_ready(sandbox)

        result = sandbox.exec("echo process-exec-ok")
        assert result.exit_code == 0
        assert "process-exec-ok" in result.stdout

        result = sandbox.exec(
            {
                "command": "bash",
                "args": ["-lc", "echo process-exec-fail 1>&2; exit 7"],
            }
        )
        assert result.exit_code == 7
        assert "process-exec-fail" in result.stderr

        stdin_process = sandbox.processes.start(
            {
                "command": "bash",
                "args": ["-lc", "read line; echo stdout:$line; echo stderr:$line 1>&2"],
            }
        )
        fetched = sandbox.get_process(stdin_process.id)
        assert fetched.id == stdin_process.id

        listing = sandbox.processes.list(limit=20)
        assert any(entry.id == stdin_process.id for entry in listing.data)

        stdin_process.write_stdin("sdk-stdin\n", eof=True)
        result = stdin_process.wait()
        assert result.exit_code == 0
        assert "stdout:sdk-stdin" in result.stdout
        assert "stderr:sdk-stdin" in result.stderr

        running_process = sandbox.processes.start(
            {"command": "bash", "args": ["-lc", "sleep 30"]}
        )
        refreshed = running_process.refresh()
        assert refreshed.status in {"queued", "running"}
        result = running_process.kill()
        assert result.status not in {"queued", "running"}

        streamed = sandbox.processes.start(
            {
                "command": "bash",
                "args": ["-lc", "echo stream-out; echo stream-err 1>&2"],
            }
        )
        events = _collect_process_stream(streamed.stream())
        assert any(
            event.type == "stdout" and "stream-out" in event.data for event in events
        )
        assert any(
            event.type == "stderr" and "stream-err" in event.data for event in events
        )
        assert any(event.type == "exit" for event in events)

        result_process = sandbox.processes.start(
            {"command": "bash", "args": ["-lc", "echo result-alias-ok"]}
        )
        result = result_process.result()
        assert result.exit_code == 0
        assert "result-alias-ok" in result.stdout

        noisy_process = sandbox.processes.start(
            {
                "command": "bash",
                "args": [
                    "-lc",
                    'yes "process-replay-window-overflow-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" | head -n 120000',
                ],
            }
        )
        result = noisy_process.result()
        assert len(result.stdout) > 3 * 1024 * 1024

        expect_hyperbrowser_error(
            "process replay window expired",
            lambda: _collect_process_stream(noisy_process.stream(1)),
            status_code=410,
            code="replay_window_expired",
            service="runtime",
            retryable=False,
            message_includes="Replay window expired",
        )

        timeout_process = sandbox.processes.start(
            {"command": "bash", "args": ["-lc", "sleep 10"]}
        )
        expect_hyperbrowser_error(
            "process wait timeout",
            lambda: timeout_process.wait(timeout_ms=100),
            status_code=408,
            service="runtime",
            retryable=False,
            message_includes="timed out",
        )
        timeout_process.signal("TERM")
        result = timeout_process.wait(timeout_ms=3000)
        assert result.status in {"exited", "failed", "killed", "timed_out"}

        kill_process = sandbox.processes.start(
            {"command": "bash", "args": ["-lc", "sleep 30"]}
        )
        result = kill_process.kill()
        assert result.status not in {"queued", "running"}
        assert kill_process.status not in {"queued", "running"}

        expect_hyperbrowser_error(
            "missing process get",
            lambda: sandbox.get_process("proc_missing"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes="not found",
        )
    finally:
        stop_sandbox_if_running(sandbox)
