import asyncio

import pytest

from tests.helpers.config import create_async_client
from tests.helpers.errors import expect_hyperbrowser_error_async
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_runtime_ready_async,
)


async def _collect_terminal_session(connection):
    output = ""
    exit_code = None

    async for event in connection.events():
        if event.type == "output":
            output += event.data
            continue
        exit_code = event.status.exit_code
        break

    return output, exit_code


def _terminal_status_output(status) -> str:
    return "".join(chunk.data for chunk in ((status.output if status else None) or []))


def _terminal_status_raw_output(status) -> str:
    return b"".join(chunk.raw for chunk in ((status.output if status else None) or [])).decode(
        "utf-8"
    )


async def _wait_for_terminal_status_output(
    read_status,
    marker: str,
    timeout_seconds: float = 5.0,
):
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_status = None

    while asyncio.get_running_loop().time() < deadline:
        last_status = await read_status()
        if marker in _terminal_status_output(last_status):
            return last_status
        await asyncio.sleep(0.1)

    raise AssertionError(
        f"timed out waiting for terminal output {marker!r}; "
        f"last output={_terminal_status_output(last_status)!r}"
    )


@pytest.mark.anyio
async def test_async_sandbox_terminal_e2e():
    client = create_async_client()
    sandbox = None

    try:
        sandbox = await client.sandboxes.create(default_sandbox_params("py-async-terminal"))
        await wait_for_runtime_ready_async(sandbox)

        assert sandbox.pty is sandbox.terminal

        terminal = await sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-l"],
                "rows": 24,
                "cols": 80,
            }
        )
        fetched = await sandbox.terminal.get(terminal.id)
        assert fetched.id == terminal.id

        connection = await terminal.attach()
        try:
            await terminal.resize(30, 100)
            await connection.write("pwd\n")
            await connection.write("echo terminal-smoke-ok\n")
            await connection.write("exit\n")

            output, exit_code = await _collect_terminal_session(connection)
            assert "terminal-smoke-ok" in output
            assert exit_code == 0
        finally:
            await connection.close()

        status = await terminal.wait(timeout_ms=2000)
        assert status.running is False
        assert status.exit_code == 0

        terminal = await sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-l"],
                "rows": 24,
                "cols": 80,
            }
        )
        connection = await terminal.attach()
        try:
            await connection.resize(32, 110)
            refreshed = await terminal.refresh()
            assert refreshed.current.rows == 32
            assert refreshed.current.cols == 110

            await connection.write("exit\n")
            _, exit_code = await _collect_terminal_session(connection)
            assert exit_code == 0
        finally:
            await connection.close()

        status = await terminal.wait(timeout_ms=2000)
        assert status.running is False

        marker = "terminal-get-output"
        terminal = await sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-lc", f"printf '{marker}' && sleep 1"],
                "rows": 24,
                "cols": 80,
            }
        )
        without_output = await sandbox.terminal.get(terminal.id)
        assert without_output.current.output is None
        fetched = await _wait_for_terminal_status_output(
            lambda: _get_terminal_status(sandbox, terminal.id, include_output=True),
            marker,
        )
        assert marker in _terminal_status_output(fetched)
        assert marker in _terminal_status_raw_output(fetched)
        assert fetched.output
        status = await terminal.wait(timeout_ms=2000)
        assert status.running is False
        assert status.exit_code == 0

        marker = "terminal-refresh-output"
        terminal = await sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-lc", f"printf '{marker}' && sleep 1"],
                "rows": 24,
                "cols": 80,
            }
        )
        without_output = await terminal.refresh()
        assert without_output.current.output is None
        refreshed = await _wait_for_terminal_status_output(
            lambda: _refresh_terminal_status(terminal, include_output=True),
            marker,
        )
        assert marker in _terminal_status_output(refreshed)
        assert marker in _terminal_status_raw_output(refreshed)
        assert refreshed.output
        status = await terminal.wait(timeout_ms=2000)
        assert status.running is False
        assert status.exit_code == 0

        marker = "terminal-wait-output"
        terminal = await sandbox.terminal.create(
            {
                "command": "bash",
                "args": ["-lc", f"printf '{marker}'"],
                "rows": 24,
                "cols": 80,
            }
        )
        status = await terminal.wait(timeout_ms=2000, include_output=True)
        assert status.running is False
        assert status.exit_code == 0
        assert marker in _terminal_status_output(status)
        assert marker in _terminal_status_raw_output(status)
        assert status.output

        timeout_terminal = await sandbox.pty.create(
            {
                "command": "bash",
                "args": ["-lc", "sleep 10"],
                "rows": 24,
                "cols": 80,
            }
        )
        await expect_hyperbrowser_error_async(
            "terminal wait timeout",
            lambda: timeout_terminal.wait(timeout_ms=100),
            status_code=408,
            service="runtime",
            retryable=False,
            message_includes="timed out",
        )

        await timeout_terminal.signal("TERM")
        status = await timeout_terminal.wait(timeout_ms=3000)
        assert status.running is False

        kill_terminal = await sandbox.pty.create(
            {
                "command": "bash",
                "args": ["-lc", "sleep 30"],
                "rows": 24,
                "cols": 80,
            }
        )
        status = await kill_terminal.kill()
        assert status.running is False
        assert kill_terminal.current.running is False

        await expect_hyperbrowser_error_async(
            "missing terminal get",
            lambda: sandbox.terminal.get("pty_missing"),
            status_code=404,
            service="runtime",
            retryable=False,
            message_includes="not found",
        )
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await client.close()


async def _get_terminal_status(sandbox, terminal_id: str, *, include_output: bool = False):
    return (await sandbox.terminal.get(terminal_id, include_output=include_output)).current


async def _refresh_terminal_status(terminal, *, include_output: bool = False):
    return (await terminal.refresh(include_output=include_output)).current
