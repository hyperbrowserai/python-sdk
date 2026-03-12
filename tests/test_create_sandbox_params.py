import pytest
from pydantic import ValidationError

from hyperbrowser.models import (
    CreateSandboxParams,
    SandboxExecParams,
    SandboxProcessListParams,
    SandboxProcessWaitParams,
)


def test_create_sandbox_params_accepts_image_source():
    params = CreateSandboxParams(image_name="node")

    assert params.model_dump(by_alias=True, exclude_none=True) == {"imageName": "node"}


def test_create_sandbox_params_accepts_snapshot_source():
    params = CreateSandboxParams(snapshot_name="snap", snapshot_id="snap-id")

    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "snapshotName": "snap",
        "snapshotId": "snap-id",
    }


def test_create_sandbox_params_rejects_camel_case_input():
    with pytest.raises(ValidationError, match="Provide exactly one start source"):
        CreateSandboxParams(**{"imageName": "node"})


@pytest.mark.parametrize(
    "payload",
    [
        {"sandboxName": "legacy"},
        {"sandbox_name": "legacy"},
    ],
)
def test_create_sandbox_params_rejects_legacy_sandbox_name(payload):
    with pytest.raises(
        ValidationError,
        match="Provide exactly one start source: snapshot_name or image_name",
    ):
        CreateSandboxParams(**payload)


def test_create_sandbox_params_rejects_multiple_sources():
    with pytest.raises(
        ValidationError,
        match="Provide exactly one start source: snapshot_name or image_name",
    ):
        CreateSandboxParams(image_name="node", snapshot_name="snap")


def test_create_sandbox_params_requires_snapshot_name_for_snapshot_id():
    with pytest.raises(ValidationError, match="snapshot_id requires snapshot_name"):
        CreateSandboxParams(snapshot_id="snap-id")


def test_sandbox_exec_params_serialize_process_timeout_sec_as_snake_case():
    params = SandboxExecParams(
        command="echo hi",
        timeout_ms=500,
        timeout_sec=7,
        use_shell=True,
    )

    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "command": "echo hi",
        "timeoutMs": 500,
        "timeout_sec": 7,
        "useShell": True,
    }


def test_sandbox_process_wait_params_serialize_timeout_sec_as_snake_case():
    params = SandboxProcessWaitParams(timeout_ms=250, timeout_sec=3)

    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "timeoutMs": 250,
        "timeout_sec": 3,
    }


def test_sandbox_process_list_params_serialize_created_filters_as_snake_case():
    params = SandboxProcessListParams(
        status=["running", "exited"],
        limit=10,
        cursor="cursor-1",
        created_after=100,
        created_before=200,
    )

    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "status": ["running", "exited"],
        "limit": 10,
        "cursor": "cursor-1",
        "created_after": 100,
        "created_before": 200,
    }
