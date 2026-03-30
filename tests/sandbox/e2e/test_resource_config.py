import pytest

from hyperbrowser.models import CreateSandboxParams

from tests.helpers.config import DEFAULT_IMAGE_NAME, create_async_client, create_client
from tests.helpers.sandbox import (
    stop_sandbox_if_running,
    stop_sandbox_if_running_async,
    wait_for_runtime_ready,
    wait_for_runtime_ready_async,
)

client = create_client()

REQUESTED_CPU = 8
REQUESTED_MEMORY_MIB = 8192
REQUESTED_DISK_MIB = 10240
MEMORY_MIN_VISIBLE_MIB = REQUESTED_MEMORY_MIB - 512
DISK_MIN_VISIBLE_MIB = REQUESTED_DISK_MIB - 512


def _exec_integer(sandbox, command: str) -> int:
    result = sandbox.exec(command)
    assert result.exit_code == 0
    return int(result.stdout.strip())


async def _exec_integer_async(sandbox, command: str) -> int:
    result = await sandbox.exec(command)
    assert result.exit_code == 0
    return int(result.stdout.strip())


def test_sandbox_resource_config_e2e():
    sandbox = None

    try:
        sandbox = client.sandboxes.create(
            CreateSandboxParams(
                image_name=DEFAULT_IMAGE_NAME,
                cpu=REQUESTED_CPU,
                memory=REQUESTED_MEMORY_MIB,
                disk=REQUESTED_DISK_MIB,
            )
        )

        assert sandbox.cpu == REQUESTED_CPU
        assert sandbox.memory == REQUESTED_MEMORY_MIB
        assert sandbox.disk == REQUESTED_DISK_MIB

        detail = sandbox.info()
        assert detail.cpu == REQUESTED_CPU
        assert detail.memory == REQUESTED_MEMORY_MIB
        assert detail.disk == REQUESTED_DISK_MIB

        reloaded = client.sandboxes.get(sandbox.id)
        assert reloaded.cpu == REQUESTED_CPU
        assert reloaded.memory == REQUESTED_MEMORY_MIB
        assert reloaded.disk == REQUESTED_DISK_MIB

        wait_for_runtime_ready(sandbox)

        cpu_count = _exec_integer(sandbox, "nproc")
        memory_mib = _exec_integer(
            sandbox,
            "awk '/MemTotal/ {printf \"%.0f\\n\", $2/1024}' /proc/meminfo",
        )
        disk_mib = _exec_integer(sandbox, "df -m / | awk 'NR==2 {print $2}'")

        assert cpu_count == REQUESTED_CPU
        assert MEMORY_MIN_VISIBLE_MIB <= memory_mib <= REQUESTED_MEMORY_MIB
        assert DISK_MIN_VISIBLE_MIB <= disk_mib <= REQUESTED_DISK_MIB
    finally:
        stop_sandbox_if_running(sandbox)


@pytest.mark.anyio
async def test_async_sandbox_resource_config_e2e():
    client = create_async_client()
    sandbox = None

    try:
        sandbox = await client.sandboxes.create(
            CreateSandboxParams(
                image_name=DEFAULT_IMAGE_NAME,
                cpu=REQUESTED_CPU,
                memory=REQUESTED_MEMORY_MIB,
                disk=REQUESTED_DISK_MIB,
            )
        )

        assert sandbox.cpu == REQUESTED_CPU
        assert sandbox.memory == REQUESTED_MEMORY_MIB
        assert sandbox.disk == REQUESTED_DISK_MIB

        detail = await sandbox.info()
        assert detail.cpu == REQUESTED_CPU
        assert detail.memory == REQUESTED_MEMORY_MIB
        assert detail.disk == REQUESTED_DISK_MIB

        reloaded = await client.sandboxes.get(sandbox.id)
        assert reloaded.cpu == REQUESTED_CPU
        assert reloaded.memory == REQUESTED_MEMORY_MIB
        assert reloaded.disk == REQUESTED_DISK_MIB

        await wait_for_runtime_ready_async(sandbox)

        cpu_count = await _exec_integer_async(sandbox, "nproc")
        memory_mib = await _exec_integer_async(
            sandbox,
            "awk '/MemTotal/ {printf \"%.0f\\n\", $2/1024}' /proc/meminfo",
        )
        disk_mib = await _exec_integer_async(
            sandbox, "df -m / | awk 'NR==2 {print $2}'"
        )

        assert cpu_count == REQUESTED_CPU
        assert MEMORY_MIN_VISIBLE_MIB <= memory_mib <= REQUESTED_MEMORY_MIB
        assert DISK_MIN_VISIBLE_MIB <= disk_mib <= REQUESTED_DISK_MIB
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await client.close()
