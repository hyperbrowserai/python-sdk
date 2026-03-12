import pytest
from pydantic import ValidationError

from hyperbrowser.models import CreateSandboxParams


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
