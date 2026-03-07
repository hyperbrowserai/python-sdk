from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import SandboxListParams, SandboxRuntimeSession

from tests.helpers.errors import expect_hyperbrowser_error_async
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running_async,
    wait_for_runtime_ready_async,
)


@pytest.mark.anyio
async def test_async_sandbox_lifecycle_e2e():
    client = AsyncHyperbrowser()
    sandbox = None
    stale_handle = None
    secondary = None

    try:
        sandbox = await client.sandboxes.create(default_sandbox_params("py-async-lifecycle"))
        stale_handle = await client.sandboxes.get(sandbox.id)
        await wait_for_runtime_ready_async(sandbox)

        assert sandbox.to_dict()["token"]
        assert sandbox.runtime.base_url
        assert sandbox.token_expires_at is not None

        session = await sandbox.create_runtime_session()
        assert session.token
        assert session.sandbox_id == sandbox.id
        assert session.runtime.base_url == sandbox.runtime.base_url

        info = await sandbox.info()
        assert info.id == sandbox.id
        await sandbox.refresh()
        assert sandbox.status == "active"

        await sandbox.connect()
        assert sandbox.status == "active"

        original_create_runtime_session = sandbox.create_runtime_session
        valid_session = await original_create_runtime_session(force_refresh=True)
        invalid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.invalid-signature"
        refresh_count = 0

        async def patched_create_runtime_session(force_refresh: bool = False):
            nonlocal refresh_count
            if force_refresh:
                refresh_count += 1
                return await original_create_runtime_session(force_refresh=True)

            return SandboxRuntimeSession(
                sandbox_id=valid_session.sandbox_id,
                status=valid_session.status,
                region=valid_session.region,
                token=invalid_jwt,
                token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                runtime=valid_session.runtime,
            )

        sandbox.create_runtime_session = patched_create_runtime_session
        try:
            result = await sandbox.exec("echo runtime-refresh-ok")
            assert result.exit_code == 0
            assert "runtime-refresh-ok" in result.stdout
            assert refresh_count > 0
            assert sandbox.to_dict()["token"]
            assert sandbox.to_dict()["token"] != invalid_jwt
        finally:
            sandbox.create_runtime_session = original_create_runtime_session

        listing = await client.sandboxes.list(
            SandboxListParams(search=sandbox.id, limit=20)
        )
        assert any(entry.id == sandbox.id for entry in listing.sandboxes)

        response = await sandbox.stop()
        assert response.success is True
        assert sandbox.status == "closed"

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
            service="control",
            retryable=False,
            message_includes="Sandbox is not running",
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

        secondary = await client.sandboxes.start_from_snapshot(
            default_sandbox_params("py-async-secondary")
        )
        response = await secondary.stop()
        assert response.success is True
        assert secondary.status == "closed"
    finally:
        await stop_sandbox_if_running_async(sandbox)
        await stop_sandbox_if_running_async(stale_handle)
        await stop_sandbox_if_running_async(secondary)
        await client.close()
