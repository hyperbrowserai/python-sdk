import asyncio

import hyperbrowser.client.managers.job_wait_utils as job_wait_utils


def test_wait_for_job_result_with_defaults_forwards_arguments():
    captured_kwargs = {}

    def _fake_wait_for_job_result(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return "result"

    original_wait = job_wait_utils.wait_for_job_result
    job_wait_utils.wait_for_job_result = _fake_wait_for_job_result
    try:
        result = job_wait_utils.wait_for_job_result_with_defaults(
            operation_name="job test",
            get_status=lambda: "running",
            is_terminal_status=lambda status: status == "completed",
            fetch_result=lambda: "payload",
            poll_interval_seconds=1.5,
            max_wait_seconds=25.0,
            max_status_failures=4,
        )
    finally:
        job_wait_utils.wait_for_job_result = original_wait

    assert result == "result"
    assert captured_kwargs["operation_name"] == "job test"
    assert captured_kwargs["poll_interval_seconds"] == 1.5
    assert captured_kwargs["max_wait_seconds"] == 25.0
    assert captured_kwargs["max_status_failures"] == 4
    assert captured_kwargs["fetch_max_attempts"] == job_wait_utils.POLLING_ATTEMPTS
    assert captured_kwargs["fetch_retry_delay_seconds"] == 0.5


def test_wait_for_job_result_with_defaults_async_forwards_arguments():
    captured_kwargs = {}

    async def _fake_wait_for_job_result_async(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return "result"

    original_wait = job_wait_utils.wait_for_job_result_async
    job_wait_utils.wait_for_job_result_async = _fake_wait_for_job_result_async
    try:
        result = asyncio.run(
            job_wait_utils.wait_for_job_result_with_defaults_async(
                operation_name="job test",
                get_status=lambda: asyncio.sleep(0, result="running"),
                is_terminal_status=lambda status: status == "completed",
                fetch_result=lambda: asyncio.sleep(0, result="payload"),
                poll_interval_seconds=1.5,
                max_wait_seconds=25.0,
                max_status_failures=4,
            )
        )
    finally:
        job_wait_utils.wait_for_job_result_async = original_wait

    assert result == "result"
    assert captured_kwargs["operation_name"] == "job test"
    assert captured_kwargs["poll_interval_seconds"] == 1.5
    assert captured_kwargs["max_wait_seconds"] == 25.0
    assert captured_kwargs["max_status_failures"] == 4
    assert captured_kwargs["fetch_max_attempts"] == job_wait_utils.POLLING_ATTEMPTS
    assert captured_kwargs["fetch_retry_delay_seconds"] == 0.5
