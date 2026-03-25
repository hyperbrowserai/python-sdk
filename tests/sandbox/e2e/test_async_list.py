import asyncio

import pytest

from hyperbrowser.models import (
    SandboxListParams,
    SandboxMemorySnapshotParams,
    SandboxSnapshotListParams,
)

from tests.helpers.config import create_async_client, make_test_name
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_created_snapshot_async,
    wait_for_runtime_ready_async,
)

SANDBOX_PAGE_LIMIT = 50
LIST_POLL_DELAY_SECONDS = 0.5
LIST_POLL_TIMEOUT_SECONDS = 90


async def _wait_for_sandbox_in_list(client, sandbox_id: str):
    deadline = asyncio.get_running_loop().time() + LIST_POLL_TIMEOUT_SECONDS

    while asyncio.get_running_loop().time() < deadline:
        page = 1

        while True:
            response = await client.sandboxes.list(
                SandboxListParams(
                    status="active",
                    page=page,
                    limit=SANDBOX_PAGE_LIMIT,
                )
            )
            match = next(
                (entry for entry in response.sandboxes if entry.id == sandbox_id),
                None,
            )
            if match is not None:
                return match

            has_more = page * response.per_page < response.total_count
            if not has_more or not response.sandboxes:
                break

            page += 1

        await asyncio.sleep(LIST_POLL_DELAY_SECONDS)

    raise RuntimeError(f"sandbox {sandbox_id} did not appear in list()")


@pytest.mark.anyio
async def test_async_sandbox_list_e2e():
    client = create_async_client()
    sandbox = None
    memory_snapshot = None
    snapshot_name = make_test_name("py-async-list-snapshot")

    try:
        sandbox = await client.sandboxes.create(default_sandbox_params("py-async-list"))

        listed_sandbox = await _wait_for_sandbox_in_list(client, sandbox.id)
        assert listed_sandbox.id == sandbox.id
        assert listed_sandbox.status == "active"
        assert listed_sandbox.region == sandbox.region
        assert listed_sandbox.runtime.transport == "regional_proxy"
        assert listed_sandbox.runtime.base_url == sandbox.runtime.base_url

        await wait_for_runtime_ready_async(sandbox)
        memory_snapshot = await sandbox.create_memory_snapshot(
            SandboxMemorySnapshotParams(snapshot_name=snapshot_name)
        )

        images = await client.sandboxes.list_images()
        listed_image = next(
            (entry for entry in images.images if entry.id == memory_snapshot.image_id),
            None,
        )
        assert listed_image is not None
        assert listed_image.image_name == memory_snapshot.image_name
        assert listed_image.namespace == memory_snapshot.image_namespace
        assert isinstance(listed_image.uploaded, bool)

        listed_snapshot = await wait_for_created_snapshot_async(
            client, memory_snapshot.snapshot_id
        )
        assert listed_snapshot.id == memory_snapshot.snapshot_id
        assert listed_snapshot.snapshot_name == snapshot_name
        assert listed_snapshot.namespace == memory_snapshot.namespace
        assert listed_snapshot.image_id == memory_snapshot.image_id
        assert listed_snapshot.image_name == memory_snapshot.image_name
        assert listed_snapshot.image_namespace == memory_snapshot.image_namespace
        assert listed_snapshot.status == "created"

        created_snapshots = await client.sandboxes.list_snapshots(
            SandboxSnapshotListParams(
                status="created",
                limit=200,
            )
        )
        assert any(
            entry.id == listed_snapshot.id for entry in created_snapshots.snapshots
        )
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await client.close()
