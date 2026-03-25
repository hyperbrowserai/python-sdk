from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hyperbrowser.models import CreateSandboxParams, SandboxRuntimeSession

from tests.helpers.config import DEFAULT_IMAGE_NAME, create_async_client
from tests.helpers.errors import expect_hyperbrowser_error_async
from tests.helpers.http import get_image_by_name_async
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_created_snapshot_async,
    wait_for_runtime_ready_async,
)

CUSTOM_IMAGE_NAME = "node"


@pytest.mark.anyio
async def test_async_sandbox_lifecycle_e2e():
    client = create_async_client()
    sandbox = None
    stale_handle = None
    secondary = None
    image_sandbox = None
    custom_image_sandbox = None
    custom_snapshot_sandbox = None
    memory_snapshot = None
    custom_image_memory_snapshot = None
    custom_image = None

    try:
        sandbox = await client.sandboxes.create(
            default_sandbox_params("py-async-lifecycle")
        )
        stale_handle = await client.sandboxes.get(sandbox.id)
        custom_image = await get_image_by_name_async(CUSTOM_IMAGE_NAME)
        await wait_for_runtime_ready_async(sandbox)

        detail = sandbox.to_dict()
        assert detail["token"]
        assert sandbox.runtime.base_url
        assert sandbox.token_expires_at is not None

        stale_detail = stale_handle.to_dict()
        assert stale_detail["token"]
        assert stale_handle.runtime.base_url == sandbox.runtime.base_url

        info = await sandbox.info()
        assert info.id == sandbox.id
        await sandbox.refresh()
        assert sandbox.status == "active"

        await sandbox.connect()
        assert sandbox.status == "active"

        memory_snapshot = await sandbox.create_memory_snapshot()
        assert memory_snapshot.snapshot_name
        assert memory_snapshot.snapshot_id
        assert memory_snapshot.namespace
        assert memory_snapshot.status
        assert memory_snapshot.image_name
        assert memory_snapshot.image_id
        assert memory_snapshot.image_namespace

        # Snapshot creation can briefly disrupt the next fast exec on the same handle.
        await wait_for_runtime_ready_async(sandbox)

        valid_detail = await sandbox.info()
        invalid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.invalid-signature"
        refresh_count = 0
        original_get_detail = sandbox._service.get_detail

        sandbox._runtime_session = SandboxRuntimeSession(
            sandbox_id=sandbox.id,
            status=valid_detail.status,
            region=valid_detail.region,
            token=invalid_jwt,
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            runtime=valid_detail.runtime,
        )
        sandbox._detail = valid_detail.model_copy(
            update={
                "token": invalid_jwt,
                "token_expires_at": sandbox._runtime_session.token_expires_at,
            }
        )

        async def patched_get_detail(sandbox_id: str):
            nonlocal refresh_count
            refresh_count += 1
            return await original_get_detail(sandbox_id)

        sandbox._service.get_detail = patched_get_detail
        try:
            result = await sandbox.exec("echo runtime-refresh-ok")
            assert result.exit_code == 0
            assert "runtime-refresh-ok" in result.stdout
            assert refresh_count > 0
            assert sandbox.to_dict()["token"]
            assert sandbox.to_dict()["token"] != invalid_jwt
        finally:
            sandbox._service.get_detail = original_get_detail

        image_sandbox = await client.sandboxes.create(
            CreateSandboxParams(image_name=DEFAULT_IMAGE_NAME)
        )
        assert image_sandbox.id
        assert image_sandbox.status == "active"
        response = await image_sandbox.stop()
        assert response.success is True
        assert image_sandbox.status == "closed"

        custom_image_sandbox = await client.sandboxes.create(
            CreateSandboxParams(
                image_name=custom_image["imageName"],
                image_id=custom_image["id"],
            )
        )
        assert custom_image_sandbox.id
        assert custom_image_sandbox.status == "active"
        await wait_for_runtime_ready_async(custom_image_sandbox)

        custom_image_memory_snapshot = (
            await custom_image_sandbox.create_memory_snapshot()
        )
        assert custom_image_memory_snapshot.image_name == custom_image["imageName"]
        assert custom_image_memory_snapshot.image_id == custom_image["id"]
        assert custom_image_memory_snapshot.image_namespace == custom_image["namespace"]

        await wait_for_created_snapshot_async(
            client, custom_image_memory_snapshot.snapshot_id
        )
        custom_snapshot_sandbox = await client.sandboxes.create(
            CreateSandboxParams(
                snapshot_name=custom_image_memory_snapshot.snapshot_name,
                snapshot_id=custom_image_memory_snapshot.snapshot_id,
            ),
        )
        assert custom_snapshot_sandbox.id
        assert custom_snapshot_sandbox.status == "active"
        response = await custom_snapshot_sandbox.stop()
        assert response.success is True
        assert custom_snapshot_sandbox.status == "closed"

        await expect_hyperbrowser_error_async(
            "mismatched image selector",
            lambda: client.sandboxes.create(
                CreateSandboxParams(
                    image_name=custom_image["imageName"],
                    image_id=str(uuid4()),
                )
            ),
            status_code=404,
            service="control",
            retryable=False,
            message_includes_any=["image not found", "not found"],
        )

        await expect_hyperbrowser_error_async(
            "mismatched snapshot selector",
            lambda: client.sandboxes.create(
                CreateSandboxParams(
                    snapshot_name=memory_snapshot.snapshot_name,
                    snapshot_id=str(uuid4()),
                )
            ),
            status_code=404,
            service="control",
            retryable=False,
            message_includes_any=["snapshot not found", "not found"],
        )

        response = await sandbox.stop()
        assert response.success is True
        assert sandbox.status == "closed"

        await expect_hyperbrowser_error_async(
            "stopped sandbox memory snapshot",
            lambda: sandbox.create_memory_snapshot(),
            status_code=409,
            service="control",
            retryable=False,
            message_includes="Sandbox is not running",
        )

        await expect_hyperbrowser_error_async(
            "stopped sandbox connect",
            lambda: sandbox.connect(),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        await expect_hyperbrowser_error_async(
            "stopped sandbox exec",
            lambda: sandbox.exec("echo should-not-run"),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        await expect_hyperbrowser_error_async(
            "stale sandbox connect",
            lambda: stale_handle.connect(),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        await expect_hyperbrowser_error_async(
            "stopped sandbox reconnect",
            lambda: client.sandboxes.connect(sandbox.id),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        await expect_hyperbrowser_error_async(
            "missing sandbox get",
            lambda: client.sandboxes.get(str(uuid4())),
            status_code=404,
            service="control",
            retryable=False,
            message_includes="not found",
        )

        await wait_for_created_snapshot_async(client, memory_snapshot.snapshot_id)
        secondary = await client.sandboxes.create(
            CreateSandboxParams(
                snapshot_name=memory_snapshot.snapshot_name,
                snapshot_id=memory_snapshot.snapshot_id,
            ),
        )
        response = await secondary.stop()
        assert response.success is True
        assert secondary.status == "closed"
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await stop_sandbox_if_running_async(stale_handle)
        await stop_sandbox_if_running_async(secondary)
        await stop_sandbox_if_running_async(image_sandbox)
        await stop_sandbox_if_running_async(custom_image_sandbox)
        await stop_sandbox_if_running_async(custom_snapshot_sandbox)
        await client.close()
