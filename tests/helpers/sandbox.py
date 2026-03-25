import time

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import CreateSandboxParams, SandboxSnapshotListParams

from tests.helpers.config import DEFAULT_IMAGE_NAME

SNAPSHOT_LIST_LIMIT = 200
LIST_POLL_DELAY_SECONDS = 0.5
LIST_POLL_TIMEOUT_SECONDS = 90


def default_sandbox_params(prefix: str) -> CreateSandboxParams:
    return CreateSandboxParams(
        image_name=DEFAULT_IMAGE_NAME,
    )


def stop_sandbox_if_running(sandbox) -> None:
    if sandbox is None:
        return

    try:
        sandbox.stop()
    except HyperbrowserError as error:
        if error.status_code in {404, 409}:
            return
        raise


def wait_for_runtime_ready(
    sandbox,
    *,
    attempts: int = 5,
    delay_seconds: float = 0.25,
) -> None:
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            result = sandbox.exec("true")
            if result.exit_code == 0:
                return
            last_error = RuntimeError(
                f"runtime readiness probe exited with code {result.exit_code}"
            )
        except HyperbrowserError as error:
            if error.service == "runtime" and error.retryable:
                last_error = error
            else:
                raise

        if attempt < attempts:
            time.sleep(delay_seconds * attempt)

    if isinstance(last_error, Exception):
        raise last_error
    raise RuntimeError("sandbox runtime did not become ready")


def wait_for_created_snapshot(
    client,
    snapshot_id: str,
    *,
    limit: int = SNAPSHOT_LIST_LIMIT,
    delay_seconds: float = LIST_POLL_DELAY_SECONDS,
    timeout_seconds: float = LIST_POLL_TIMEOUT_SECONDS,
):
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        response = client.sandboxes.list_snapshots(
            SandboxSnapshotListParams(limit=limit)
        )
        match = next(
            (entry for entry in response.snapshots if entry.id == snapshot_id),
            None,
        )
        if match is not None and match.status == "created":
            return match

        time.sleep(delay_seconds)

    raise RuntimeError(
        f"snapshot {snapshot_id} did not appear as created in list_snapshots()"
    )


async def stop_sandbox_if_running_async(sandbox) -> None:
    if sandbox is None:
        return

    try:
        await sandbox.stop()
    except HyperbrowserError as error:
        if error.status_code in {404, 409}:
            return
        raise


async def wait_for_runtime_ready_async(
    sandbox,
    *,
    attempts: int = 5,
    delay_seconds: float = 0.25,
) -> None:
    import asyncio

    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            result = await sandbox.exec("true")
            if result.exit_code == 0:
                return
            last_error = RuntimeError(
                f"runtime readiness probe exited with code {result.exit_code}"
            )
        except HyperbrowserError as error:
            if error.service == "runtime" and error.retryable:
                last_error = error
            else:
                raise

        if attempt < attempts:
            await asyncio.sleep(delay_seconds * attempt)

    if isinstance(last_error, Exception):
        raise last_error
    raise RuntimeError("sandbox runtime did not become ready")


async def wait_for_created_snapshot_async(
    client,
    snapshot_id: str,
    *,
    limit: int = SNAPSHOT_LIST_LIMIT,
    delay_seconds: float = LIST_POLL_DELAY_SECONDS,
    timeout_seconds: float = LIST_POLL_TIMEOUT_SECONDS,
):
    import asyncio

    deadline = asyncio.get_running_loop().time() + timeout_seconds

    while asyncio.get_running_loop().time() < deadline:
        response = await client.sandboxes.list_snapshots(
            SandboxSnapshotListParams(limit=limit)
        )
        match = next(
            (entry for entry in response.snapshots if entry.id == snapshot_id),
            None,
        )
        if match is not None and match.status == "created":
            return match

        await asyncio.sleep(delay_seconds)

    raise RuntimeError(
        f"snapshot {snapshot_id} did not appear as created in list_snapshots()"
    )
