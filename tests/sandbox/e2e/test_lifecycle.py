import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import SandboxRuntimeSession

from tests.helpers.config import DEFAULT_IMAGE_NAME, create_client
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.http import get_image_by_name
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()

CUSTOM_IMAGE_NAME = "node"
SNAPSHOT_CREATE_RETRY_DELAY_SECONDS = 0.5
SNAPSHOT_CREATE_RETRY_TIMEOUT_SECONDS = 60


def _create_sandbox_with_snapshot_retry(params):
    deadline = time.monotonic() + SNAPSHOT_CREATE_RETRY_TIMEOUT_SECONDS
    last_error = None

    while time.monotonic() < deadline:
        try:
            return client.sandboxes.create(params)
        except HyperbrowserError as error:
            is_snapshot_catalog_race = (
                error.status_code == 404
                and isinstance(str(error), str)
                and "snapshot not found" in str(error).lower()
            )
            if not is_snapshot_catalog_race:
                raise
            last_error = error
            time.sleep(SNAPSHOT_CREATE_RETRY_DELAY_SECONDS)

    if isinstance(last_error, Exception):
        raise last_error
    raise RuntimeError("snapshot create retry failed")


def test_sandbox_lifecycle_e2e():
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
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-lifecycle"))
        stale_handle = client.sandboxes.get(sandbox.id)
        custom_image = get_image_by_name(CUSTOM_IMAGE_NAME)
        wait_for_runtime_ready(sandbox)

        detail = sandbox.to_dict()
        assert detail["token"]
        assert sandbox.runtime.base_url
        assert sandbox.token_expires_at is not None

        stale_detail = stale_handle.to_dict()
        assert stale_detail["token"]
        assert stale_handle.runtime.base_url == sandbox.runtime.base_url

        info = sandbox.info()
        assert info.id == sandbox.id
        sandbox.refresh()
        assert sandbox.status == "active"

        sandbox.connect()
        assert sandbox.status == "active"

        memory_snapshot = sandbox.create_memory_snapshot()
        assert memory_snapshot.snapshot_name
        assert memory_snapshot.snapshot_id
        assert memory_snapshot.namespace
        assert memory_snapshot.status
        assert memory_snapshot.image_name
        assert memory_snapshot.image_id
        assert memory_snapshot.image_namespace

        # Snapshot creation can briefly disrupt the next fast exec on the same handle.
        wait_for_runtime_ready(sandbox)

        valid_detail = sandbox.info()
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

        def patched_get_detail(sandbox_id: str):
            nonlocal refresh_count
            refresh_count += 1
            return original_get_detail(sandbox_id)

        sandbox._service.get_detail = patched_get_detail
        try:
            result = sandbox.exec("echo runtime-refresh-ok")
            assert result.exit_code == 0
            assert "runtime-refresh-ok" in result.stdout
            assert refresh_count > 0
            assert sandbox.to_dict()["token"]
            assert sandbox.to_dict()["token"] != invalid_jwt
        finally:
            sandbox._service.get_detail = original_get_detail

        image_sandbox = client.sandboxes.create({"image_name": DEFAULT_IMAGE_NAME})
        assert image_sandbox.id
        assert image_sandbox.status == "active"
        response = image_sandbox.stop()
        assert response.success is True
        assert image_sandbox.status == "closed"

        custom_image_sandbox = client.sandboxes.create(
            {
                "image_name": custom_image["imageName"],
                "image_id": custom_image["id"],
            }
        )
        assert custom_image_sandbox.id
        assert custom_image_sandbox.status == "active"
        wait_for_runtime_ready(custom_image_sandbox)

        custom_image_memory_snapshot = custom_image_sandbox.create_memory_snapshot()
        assert custom_image_memory_snapshot.image_name == custom_image["imageName"]
        assert custom_image_memory_snapshot.image_id == custom_image["id"]
        assert custom_image_memory_snapshot.image_namespace == custom_image["namespace"]

        custom_snapshot_sandbox = _create_sandbox_with_snapshot_retry(
            {
                "snapshot_name": custom_image_memory_snapshot.snapshot_name,
                "snapshot_id": custom_image_memory_snapshot.snapshot_id,
            }
        )
        assert custom_snapshot_sandbox.id
        assert custom_snapshot_sandbox.status == "active"
        response = custom_snapshot_sandbox.stop()
        assert response.success is True
        assert custom_snapshot_sandbox.status == "closed"

        expect_hyperbrowser_error(
            "mismatched image selector",
            lambda: client.sandboxes.create(
                {
                    "image_name": custom_image["imageName"],
                    "image_id": str(uuid4()),
                }
            ),
            status_code=404,
            service="control",
            retryable=False,
            message_includes_any=["image not found", "not found"],
        )

        expect_hyperbrowser_error(
            "mismatched snapshot selector",
            lambda: client.sandboxes.create(
                {
                    "snapshot_name": memory_snapshot.snapshot_name,
                    "snapshot_id": str(uuid4()),
                }
            ),
            status_code=404,
            service="control",
            retryable=False,
            message_includes_any=["snapshot not found", "not found"],
        )

        response = sandbox.stop()
        assert response.success is True
        assert sandbox.status == "closed"

        expect_hyperbrowser_error(
            "stopped sandbox memory snapshot",
            lambda: sandbox.create_memory_snapshot(),
            status_code=409,
            service="control",
            retryable=False,
            message_includes="Sandbox is not running",
        )

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
            code="sandbox_not_running",
            service="runtime",
            retryable=False,
            message_includes="not running",
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

        secondary = _create_sandbox_with_snapshot_retry(
            {
                "snapshot_name": memory_snapshot.snapshot_name,
                "snapshot_id": memory_snapshot.snapshot_id,
            }
        )
        response = secondary.stop()
        assert response.success is True
        assert secondary.status == "closed"
    finally:
        stop_sandbox_if_running(sandbox)
        stop_sandbox_if_running(stale_handle)
        stop_sandbox_if_running(secondary)
        stop_sandbox_if_running(image_sandbox)
        stop_sandbox_if_running(custom_image_sandbox)
        stop_sandbox_if_running(custom_snapshot_sandbox)
