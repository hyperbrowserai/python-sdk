from datetime import datetime, timedelta, timezone
from uuid import uuid4

from hyperbrowser.models import SandboxListParams, SandboxRuntimeSession

from tests.helpers.config import create_client
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()


def test_sandbox_lifecycle_e2e():
    sandbox = None
    stale_handle = None
    secondary = None

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-lifecycle"))
        stale_handle = client.sandboxes.get(sandbox.id)
        wait_for_runtime_ready(sandbox)

        assert sandbox.to_dict()["token"]
        assert sandbox.runtime.base_url
        assert sandbox.token_expires_at is not None

        session = sandbox.create_runtime_session()
        assert session.token
        assert session.sandbox_id == sandbox.id
        assert session.runtime.base_url == sandbox.runtime.base_url

        info = sandbox.info()
        assert info.id == sandbox.id
        sandbox.refresh()
        assert sandbox.status == "active"

        sandbox.connect()
        assert sandbox.status == "active"

        original_create_runtime_session = sandbox.create_runtime_session
        valid_session = original_create_runtime_session(force_refresh=True)
        invalid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.invalid-signature"
        refresh_count = 0

        def patched_create_runtime_session(force_refresh: bool = False):
            nonlocal refresh_count
            if force_refresh:
                refresh_count += 1
                return original_create_runtime_session(force_refresh=True)

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
            result = sandbox.exec("echo runtime-refresh-ok")
            assert result.exit_code == 0
            assert "runtime-refresh-ok" in result.stdout
            assert refresh_count > 0
            assert sandbox.to_dict()["token"]
            assert sandbox.to_dict()["token"] != invalid_jwt
        finally:
            sandbox.create_runtime_session = original_create_runtime_session

        listing = client.sandboxes.list(
            SandboxListParams(search=sandbox.id, limit=20)
        )
        assert any(entry.id == sandbox.id for entry in listing.sandboxes)

        response = sandbox.stop()
        assert response.success is True
        assert sandbox.status == "closed"

        expect_hyperbrowser_error(
            "stopped sandbox connect",
            lambda: sandbox.connect(),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        expect_hyperbrowser_error(
            "stopped sandbox exec",
            lambda: sandbox.exec("echo should-not-run"),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        expect_hyperbrowser_error(
            "stale sandbox connect",
            lambda: stale_handle.connect(),
            status_code=409,
            service="control",
            retryable=False,
            message_includes="Sandbox is not running",
        )

        expect_hyperbrowser_error(
            "stopped sandbox reconnect",
            lambda: client.sandboxes.connect(sandbox.id),
            status_code=409,
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
        )

        expect_hyperbrowser_error(
            "missing sandbox get",
            lambda: client.sandboxes.get(str(uuid4())),
            status_code=404,
            service="control",
            retryable=False,
            message_includes="not found",
        )

        secondary = client.sandboxes.start_from_snapshot(
            default_sandbox_params("py-sdk-secondary")
        )
        response = secondary.stop()
        assert response.success is True
        assert secondary.status == "closed"
    finally:
        stop_sandbox_if_running(sandbox)
        stop_sandbox_if_running(stale_handle)
        stop_sandbox_if_running(secondary)
