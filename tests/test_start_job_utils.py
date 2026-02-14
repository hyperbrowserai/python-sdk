import pytest

import hyperbrowser.client.managers.start_job_utils as start_job_utils
from hyperbrowser.exceptions import HyperbrowserError


def test_build_started_job_context_returns_job_id_and_operation_name():
    job_id, operation_name = start_job_utils.build_started_job_context(
        started_job_id="job-1",
        start_error_message="failed start",
        operation_name_prefix="test job ",
    )

    assert job_id == "job-1"
    assert operation_name == "test job job-1"


def test_build_started_job_context_wraps_missing_job_id_error_message():
    with pytest.raises(HyperbrowserError, match="failed start"):
        start_job_utils.build_started_job_context(
            started_job_id=None,
            start_error_message="failed start",
            operation_name_prefix="test job ",
        )


def test_build_started_job_context_preserves_operation_name_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        start_job_utils,
        "build_operation_name",
        lambda prefix, job_id: (_ for _ in ()).throw(
            HyperbrowserError("custom operation-name failure")
        ),
    )

    with pytest.raises(
        HyperbrowserError, match="custom operation-name failure"
    ) as exc_info:
        start_job_utils.build_started_job_context(
            started_job_id="job-1",
            start_error_message="failed start",
            operation_name_prefix="test job ",
        )

    assert exc_info.value.original_error is None
