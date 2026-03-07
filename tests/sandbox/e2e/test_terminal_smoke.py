from tests.helpers.config import create_client
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()


def _collect_terminal_session(connection):
    output = ""
    exit_code = None

    for event in connection.events():
        if event.type == "output":
            output += event.data
            continue
        exit_code = event.status.exit_code
        break

    return output, exit_code


def test_sandbox_terminal_e2e():
    sandbox = None

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-terminal"))
        wait_for_runtime_ready(sandbox)

        assert sandbox.pty is sandbox.terminal

        terminal = sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-l"],
                "rows": 24,
                "cols": 80,
            }
        )
        fetched = sandbox.terminal.get(terminal.id)
        assert fetched.id == terminal.id

        connection = terminal.attach()
        try:
            terminal.resize(30, 100)
            connection.write("pwd\n")
            connection.write("echo terminal-smoke-ok\n")
            connection.write("exit\n")

            output, exit_code = _collect_terminal_session(connection)
            assert "terminal-smoke-ok" in output
            assert exit_code == 0
        finally:
            connection.close()

        status = terminal.wait(timeout_ms=2000)
        assert status.running is False
        assert status.exit_code == 0

        terminal = sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-l"],
                "rows": 24,
                "cols": 80,
            }
        )
        connection = terminal.attach()
        try:
            connection.resize(32, 110)
            refreshed = terminal.refresh()
            assert refreshed.current.rows == 32
            assert refreshed.current.cols == 110

            connection.write("exit\n")
            _, exit_code = _collect_terminal_session(connection)
            assert exit_code == 0
        finally:
            connection.close()

        status = terminal.wait(timeout_ms=2000)
        assert status.running is False

        timeout_terminal = sandbox.pty.create(
            {
                "command": "bash",
                "args": ["-lc", "sleep 10"],
                "rows": 24,
                "cols": 80,
            }
        )
        expect_hyperbrowser_error(
            "terminal wait timeout",
            lambda: timeout_terminal.wait(timeout_ms=100),
            status_code=408,
            service="runtime",
            retryable=False,
            message_includes="timed out",
        )

        timeout_terminal.signal("TERM")
        status = timeout_terminal.wait(timeout_ms=3000)
        assert status.running is False

        kill_terminal = sandbox.pty.create(
            {
                "command": "bash",
                "args": ["-lc", "sleep 30"],
                "rows": 24,
                "cols": 80,
            }
        )
        status = kill_terminal.kill()
        assert status.running is False
        assert kill_terminal.current.running is False

        expect_hyperbrowser_error(
            "missing terminal get",
            lambda: sandbox.terminal.get("pty_missing"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes="not found",
        )
    finally:
        stop_sandbox_if_running(sandbox)
