import asyncio

import hyperbrowser.client.managers.job_poll_utils as job_poll_utils


def test_poll_job_until_terminal_status_forwards_arguments():
    captured_kwargs = {}

    def _fake_poll_until_terminal_status(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return "completed"

    original_poll = job_poll_utils.poll_until_terminal_status
    job_poll_utils.poll_until_terminal_status = _fake_poll_until_terminal_status
    try:
        result = job_poll_utils.poll_job_until_terminal_status(
            operation_name="job poll",
            get_status=lambda: "running",
            is_terminal_status=lambda status: status == "completed",
            poll_interval_seconds=2.5,
            max_wait_seconds=20.0,
            max_status_failures=4,
        )
    finally:
        job_poll_utils.poll_until_terminal_status = original_poll

    assert result == "completed"
    assert captured_kwargs["operation_name"] == "job poll"
    assert captured_kwargs["poll_interval_seconds"] == 2.5
    assert captured_kwargs["max_wait_seconds"] == 20.0
    assert captured_kwargs["max_status_failures"] == 4


def test_poll_job_until_terminal_status_async_forwards_arguments():
    captured_kwargs = {}

    async def _fake_poll_until_terminal_status_async(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return "completed"

    original_poll = job_poll_utils.poll_until_terminal_status_async
    job_poll_utils.poll_until_terminal_status_async = (
        _fake_poll_until_terminal_status_async
    )
    try:
        result = asyncio.run(
            job_poll_utils.poll_job_until_terminal_status_async(
                operation_name="job poll",
                get_status=lambda: asyncio.sleep(0, result="running"),
                is_terminal_status=lambda status: status == "completed",
                poll_interval_seconds=2.5,
                max_wait_seconds=20.0,
                max_status_failures=4,
            )
        )
    finally:
        job_poll_utils.poll_until_terminal_status_async = original_poll

    assert result == "completed"
    assert captured_kwargs["operation_name"] == "job poll"
    assert captured_kwargs["poll_interval_seconds"] == 2.5
    assert captured_kwargs["max_wait_seconds"] == 20.0
    assert captured_kwargs["max_status_failures"] == 4
