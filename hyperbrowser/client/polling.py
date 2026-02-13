import asyncio
import time
from typing import Awaitable, Callable, Optional, TypeVar

from hyperbrowser.exceptions import (
    HyperbrowserError,
    HyperbrowserPollingError,
    HyperbrowserTimeoutError,
)

T = TypeVar("T")


def has_exceeded_max_wait(start_time: float, max_wait_seconds: Optional[float]) -> bool:
    return (
        max_wait_seconds is not None
        and (time.monotonic() - start_time) > max_wait_seconds
    )


def poll_until_terminal_status(
    *,
    operation_name: str,
    get_status: Callable[[], str],
    is_terminal_status: Callable[[str], bool],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int = 5,
) -> str:
    start_time = time.monotonic()
    failures = 0

    while True:
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
            )

        try:
            status = get_status()
            failures = 0
        except Exception as exc:
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    f"Failed to poll {operation_name} after {max_status_failures} attempts: {exc}"
                ) from exc
            time.sleep(poll_interval_seconds)
            continue

        if is_terminal_status(status):
            return status
        time.sleep(poll_interval_seconds)


def retry_operation(
    *,
    operation_name: str,
    operation: Callable[[], T],
    max_attempts: int,
    retry_delay_seconds: float,
) -> T:
    failures = 0
    while True:
        try:
            return operation()
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: {exc}"
                ) from exc
            time.sleep(retry_delay_seconds)


async def poll_until_terminal_status_async(
    *,
    operation_name: str,
    get_status: Callable[[], Awaitable[str]],
    is_terminal_status: Callable[[str], bool],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int = 5,
) -> str:
    start_time = time.monotonic()
    failures = 0

    while True:
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
            )

        try:
            status = await get_status()
            failures = 0
        except Exception as exc:
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    f"Failed to poll {operation_name} after {max_status_failures} attempts: {exc}"
                ) from exc
            await asyncio.sleep(poll_interval_seconds)
            continue

        if is_terminal_status(status):
            return status
        await asyncio.sleep(poll_interval_seconds)


async def retry_operation_async(
    *,
    operation_name: str,
    operation: Callable[[], Awaitable[T]],
    max_attempts: int,
    retry_delay_seconds: float,
) -> T:
    failures = 0
    while True:
        try:
            return await operation()
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: {exc}"
                ) from exc
            await asyncio.sleep(retry_delay_seconds)


def collect_paginated_results(
    *,
    operation_name: str,
    get_next_page: Callable[[int], T],
    get_current_page_batch: Callable[[T], int],
    get_total_page_batches: Callable[[T], int],
    on_page_success: Callable[[T], None],
    max_wait_seconds: Optional[float],
    max_attempts: int,
    retry_delay_seconds: float,
) -> None:
    start_time = time.monotonic()
    current_page_batch = 0
    total_page_batches = 0
    first_check = True
    failures = 0

    while first_check or current_page_batch < total_page_batches:
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out fetching paginated results for {operation_name} after {max_wait_seconds} seconds"
            )
        try:
            page_response = get_next_page(current_page_batch + 1)
            on_page_success(page_response)
            current_page_batch = get_current_page_batch(page_response)
            total_page_batches = get_total_page_batches(page_response)
            failures = 0
            first_check = False
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"Failed to fetch page batch {current_page_batch + 1} for {operation_name} after {max_attempts} attempts: {exc}"
                ) from exc
        time.sleep(retry_delay_seconds)


async def collect_paginated_results_async(
    *,
    operation_name: str,
    get_next_page: Callable[[int], Awaitable[T]],
    get_current_page_batch: Callable[[T], int],
    get_total_page_batches: Callable[[T], int],
    on_page_success: Callable[[T], None],
    max_wait_seconds: Optional[float],
    max_attempts: int,
    retry_delay_seconds: float,
) -> None:
    start_time = time.monotonic()
    current_page_batch = 0
    total_page_batches = 0
    first_check = True
    failures = 0

    while first_check or current_page_batch < total_page_batches:
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out fetching paginated results for {operation_name} after {max_wait_seconds} seconds"
            )
        try:
            page_response = await get_next_page(current_page_batch + 1)
            on_page_success(page_response)
            current_page_batch = get_current_page_batch(page_response)
            total_page_batches = get_total_page_batches(page_response)
            failures = 0
            first_check = False
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"Failed to fetch page batch {current_page_batch + 1} for {operation_name} after {max_attempts} attempts: {exc}"
                ) from exc
        await asyncio.sleep(retry_delay_seconds)


def wait_for_job_result(
    *,
    operation_name: str,
    get_status: Callable[[], str],
    is_terminal_status: Callable[[str], bool],
    fetch_result: Callable[[], T],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int,
    fetch_max_attempts: int,
    fetch_retry_delay_seconds: float,
) -> T:
    poll_until_terminal_status(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
    )
    return retry_operation(
        operation_name=f"Fetching {operation_name}",
        operation=fetch_result,
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
    )


async def wait_for_job_result_async(
    *,
    operation_name: str,
    get_status: Callable[[], Awaitable[str]],
    is_terminal_status: Callable[[str], bool],
    fetch_result: Callable[[], Awaitable[T]],
    poll_interval_seconds: float,
    max_wait_seconds: Optional[float],
    max_status_failures: int,
    fetch_max_attempts: int,
    fetch_retry_delay_seconds: float,
) -> T:
    await poll_until_terminal_status_async(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
    )
    return await retry_operation_async(
        operation_name=f"Fetching {operation_name}",
        operation=fetch_result,
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
    )
