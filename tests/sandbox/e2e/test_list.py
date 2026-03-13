import time

from hyperbrowser.models import (
    SandboxListParams,
    SandboxMemorySnapshotParams,
    SandboxSnapshotListParams,
)

from tests.helpers.config import create_client, make_test_name
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()

SANDBOX_PAGE_LIMIT = 50
SNAPSHOT_LIST_LIMIT = 200
LIST_POLL_DELAY_SECONDS = 0.5
LIST_POLL_TIMEOUT_SECONDS = 90


def _wait_for_sandbox_in_list(sandbox_id: str):
    deadline = time.monotonic() + LIST_POLL_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        page = 1

        while True:
            response = client.sandboxes.list(
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

        time.sleep(LIST_POLL_DELAY_SECONDS)

    raise RuntimeError(f"sandbox {sandbox_id} did not appear in list()")


def _wait_for_created_snapshot(snapshot_id: str):
    deadline = time.monotonic() + LIST_POLL_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        response = client.sandboxes.list_snapshots(
            SandboxSnapshotListParams(limit=SNAPSHOT_LIST_LIMIT)
        )
        match = next(
            (entry for entry in response.snapshots if entry.id == snapshot_id),
            None,
        )
        if match is not None and match.status == "created":
            return match

        time.sleep(LIST_POLL_DELAY_SECONDS)

    raise RuntimeError(
        f"snapshot {snapshot_id} did not appear as created in list_snapshots()"
    )


def test_sandbox_list_e2e():
    sandbox = None
    memory_snapshot = None
    snapshot_name = make_test_name("py-sdk-list-snapshot")

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-list"))
        wait_for_runtime_ready(sandbox)

        memory_snapshot = sandbox.create_memory_snapshot(
            SandboxMemorySnapshotParams(snapshot_name=snapshot_name)
        )

        listed_sandbox = _wait_for_sandbox_in_list(sandbox.id)
        assert listed_sandbox.id == sandbox.id
        assert listed_sandbox.status == "active"
        assert listed_sandbox.region == sandbox.region
        assert listed_sandbox.runtime.transport == "regional_proxy"
        assert listed_sandbox.runtime.base_url == sandbox.runtime.base_url

        images = client.sandboxes.list_images()
        listed_image = next(
            (entry for entry in images.images if entry.id == memory_snapshot.image_id),
            None,
        )
        assert listed_image is not None
        assert listed_image.image_name == memory_snapshot.image_name
        assert listed_image.namespace == memory_snapshot.image_namespace
        assert isinstance(listed_image.uploaded, bool)

        listed_snapshot = _wait_for_created_snapshot(memory_snapshot.snapshot_id)
        assert listed_snapshot.id == memory_snapshot.snapshot_id
        assert listed_snapshot.snapshot_name == snapshot_name
        assert listed_snapshot.namespace == memory_snapshot.namespace
        assert listed_snapshot.image_id == memory_snapshot.image_id
        assert listed_snapshot.image_name == memory_snapshot.image_name
        assert listed_snapshot.image_namespace == memory_snapshot.image_namespace
        assert listed_snapshot.status == "created"

        created_snapshots = client.sandboxes.list_snapshots(
            SandboxSnapshotListParams(
                status="created",
                limit=SNAPSHOT_LIST_LIMIT,
            )
        )
        assert any(
            entry.id == listed_snapshot.id for entry in created_snapshots.snapshots
        )
    finally:
        stop_sandbox_if_running(sandbox)
