from hyperbrowser.client.managers.job_status_utils import (
    DEFAULT_TERMINAL_JOB_STATUSES,
    is_default_terminal_job_status,
)


def test_default_terminal_job_statuses_constant_contains_expected_values():
    assert DEFAULT_TERMINAL_JOB_STATUSES == {"completed", "failed"}


def test_is_default_terminal_job_status_returns_true_for_terminal_values():
    assert is_default_terminal_job_status("completed") is True
    assert is_default_terminal_job_status("failed") is True


def test_is_default_terminal_job_status_returns_false_for_non_terminal_values():
    assert is_default_terminal_job_status("running") is False
    assert is_default_terminal_job_status("pending") is False
