from typing import Awaitable, Callable, Optional

from ..polling import poll_until_terminal_status, poll_until_terminal_status_async


def poll_job_until_terminal_status(
    *,
    operation_name: str,
    get_status: Callable[[], str],
    is_terminal_status: Callable[[str], bool],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int,
) -> str:
    return poll_until_terminal_status(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
    )


async def poll_job_until_terminal_status_async(
    *,
    operation_name: str,
    get_status: Callable[[], Awaitable[str]],
    is_terminal_status: Callable[[str], bool],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int,
) -> str:
    return await poll_until_terminal_status_async(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
    )
