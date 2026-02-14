from typing import Awaitable, Callable, Optional, TypeVar

from ..polling import wait_for_job_result, wait_for_job_result_async
from .polling_defaults import (
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLLING_RETRY_DELAY_SECONDS,
)

T = TypeVar("T")


def wait_for_job_result_with_defaults(
    *,
    operation_name: str,
    get_status: Callable[[], str],
    is_terminal_status: Callable[[str], bool],
    fetch_result: Callable[[], T],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int,
) -> T:
    return wait_for_job_result(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        fetch_result=fetch_result,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
        fetch_max_attempts=DEFAULT_POLLING_RETRY_ATTEMPTS,
        fetch_retry_delay_seconds=DEFAULT_POLLING_RETRY_DELAY_SECONDS,
    )


async def wait_for_job_result_with_defaults_async(
    *,
    operation_name: str,
    get_status: Callable[[], Awaitable[str]],
    is_terminal_status: Callable[[str], bool],
    fetch_result: Callable[[], Awaitable[T]],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int,
) -> T:
    return await wait_for_job_result_async(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        fetch_result=fetch_result,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
        fetch_max_attempts=DEFAULT_POLLING_RETRY_ATTEMPTS,
        fetch_retry_delay_seconds=DEFAULT_POLLING_RETRY_DELAY_SECONDS,
    )
