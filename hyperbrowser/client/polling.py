import asyncio
from numbers import Real
import time
from typing import Awaitable, Callable, Optional, TypeVar

from hyperbrowser.exceptions import (
    HyperbrowserError,
    HyperbrowserPollingError,
    HyperbrowserTimeoutError,
)

T = TypeVar("T")


def _validate_operation_name(operation_name: str) -> None:
    if not isinstance(operation_name, str):
        raise HyperbrowserError("operation_name must be a string")
    if not operation_name.strip():
        raise HyperbrowserError("operation_name must not be empty")


def _validate_retry_config(
    *,
    max_attempts: int,
    retry_delay_seconds: float,
    max_status_failures: Optional[int] = None,
) -> None:
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise HyperbrowserError("max_attempts must be an integer")
    if max_attempts < 1:
        raise HyperbrowserError("max_attempts must be at least 1")
    if isinstance(retry_delay_seconds, bool) or not isinstance(
        retry_delay_seconds, Real
    ):
        raise HyperbrowserError("retry_delay_seconds must be a number")
    if retry_delay_seconds < 0:
        raise HyperbrowserError("retry_delay_seconds must be non-negative")
    if max_status_failures is not None:
        if isinstance(max_status_failures, bool) or not isinstance(
            max_status_failures, int
        ):
            raise HyperbrowserError("max_status_failures must be an integer")
        if max_status_failures < 1:
            raise HyperbrowserError("max_status_failures must be at least 1")


def _validate_poll_interval(poll_interval_seconds: float) -> None:
    if isinstance(poll_interval_seconds, bool) or not isinstance(
        poll_interval_seconds, Real
    ):
        raise HyperbrowserError("poll_interval_seconds must be a number")
    if poll_interval_seconds < 0:
        raise HyperbrowserError("poll_interval_seconds must be non-negative")


def _validate_max_wait_seconds(max_wait_seconds: Optional[float]) -> None:
    if max_wait_seconds is not None and (
        isinstance(max_wait_seconds, bool) or not isinstance(max_wait_seconds, Real)
    ):
        raise HyperbrowserError("max_wait_seconds must be a number")
    if max_wait_seconds is not None and max_wait_seconds < 0:
        raise HyperbrowserError("max_wait_seconds must be non-negative")


def _validate_page_batch_values(
    *,
    operation_name: str,
    current_page_batch: int,
    total_page_batches: int,
) -> None:
    if isinstance(current_page_batch, bool) or not isinstance(current_page_batch, int):
        raise HyperbrowserPollingError(
            f"Invalid current page batch for {operation_name}: expected integer"
        )
    if isinstance(total_page_batches, bool) or not isinstance(total_page_batches, int):
        raise HyperbrowserPollingError(
            f"Invalid total page batches for {operation_name}: expected integer"
        )
    if total_page_batches < 0:
        raise HyperbrowserPollingError(
            f"Invalid total page batches for {operation_name}: must be non-negative"
        )
    if current_page_batch < 0:
        raise HyperbrowserPollingError(
            f"Invalid current page batch for {operation_name}: must be non-negative"
        )
    if total_page_batches > 0 and current_page_batch < 1:
        raise HyperbrowserPollingError(
            f"Invalid current page batch for {operation_name}: must be at least 1 when total batches are positive"
        )
    if current_page_batch > total_page_batches:
        raise HyperbrowserPollingError(
            f"Invalid page batch state for {operation_name}: current page batch {current_page_batch} exceeds total page batches {total_page_batches}"
        )


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
    _validate_operation_name(operation_name)
    _validate_poll_interval(poll_interval_seconds)
    _validate_max_wait_seconds(max_wait_seconds)
    _validate_retry_config(
        max_attempts=1,
        retry_delay_seconds=0,
        max_status_failures=max_status_failures,
    )
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
    _validate_operation_name(operation_name)
    _validate_retry_config(
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
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
    _validate_operation_name(operation_name)
    _validate_poll_interval(poll_interval_seconds)
    _validate_max_wait_seconds(max_wait_seconds)
    _validate_retry_config(
        max_attempts=1,
        retry_delay_seconds=0,
        max_status_failures=max_status_failures,
    )
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
    _validate_operation_name(operation_name)
    _validate_retry_config(
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
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
    _validate_operation_name(operation_name)
    _validate_max_wait_seconds(max_wait_seconds)
    _validate_retry_config(
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    start_time = time.monotonic()
    current_page_batch = 0
    total_page_batches = 0
    first_check = True
    failures = 0
    stagnation_failures = 0

    while first_check or current_page_batch < total_page_batches:
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out fetching paginated results for {operation_name} after {max_wait_seconds} seconds"
            )
        should_sleep = True
        try:
            previous_page_batch = current_page_batch
            page_response = get_next_page(current_page_batch + 1)
            on_page_success(page_response)
            current_page_batch = get_current_page_batch(page_response)
            total_page_batches = get_total_page_batches(page_response)
            _validate_page_batch_values(
                operation_name=operation_name,
                current_page_batch=current_page_batch,
                total_page_batches=total_page_batches,
            )
            failures = 0
            first_check = False
            if (
                current_page_batch < total_page_batches
                and current_page_batch <= previous_page_batch
            ):
                stagnation_failures += 1
                if stagnation_failures >= max_attempts:
                    raise HyperbrowserPollingError(
                        f"No pagination progress for {operation_name} after {max_attempts} attempts (stuck on page batch {current_page_batch} of {total_page_batches})"
                    )
            else:
                stagnation_failures = 0
            should_sleep = current_page_batch < total_page_batches
        except HyperbrowserPollingError:
            raise
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"Failed to fetch page batch {current_page_batch + 1} for {operation_name} after {max_attempts} attempts: {exc}"
                ) from exc
        if should_sleep:
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
    _validate_operation_name(operation_name)
    _validate_max_wait_seconds(max_wait_seconds)
    _validate_retry_config(
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    start_time = time.monotonic()
    current_page_batch = 0
    total_page_batches = 0
    first_check = True
    failures = 0
    stagnation_failures = 0

    while first_check or current_page_batch < total_page_batches:
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out fetching paginated results for {operation_name} after {max_wait_seconds} seconds"
            )
        should_sleep = True
        try:
            previous_page_batch = current_page_batch
            page_response = await get_next_page(current_page_batch + 1)
            on_page_success(page_response)
            current_page_batch = get_current_page_batch(page_response)
            total_page_batches = get_total_page_batches(page_response)
            _validate_page_batch_values(
                operation_name=operation_name,
                current_page_batch=current_page_batch,
                total_page_batches=total_page_batches,
            )
            failures = 0
            first_check = False
            if (
                current_page_batch < total_page_batches
                and current_page_batch <= previous_page_batch
            ):
                stagnation_failures += 1
                if stagnation_failures >= max_attempts:
                    raise HyperbrowserPollingError(
                        f"No pagination progress for {operation_name} after {max_attempts} attempts (stuck on page batch {current_page_batch} of {total_page_batches})"
                    )
            else:
                stagnation_failures = 0
            should_sleep = current_page_batch < total_page_batches
        except HyperbrowserPollingError:
            raise
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"Failed to fetch page batch {current_page_batch + 1} for {operation_name} after {max_attempts} attempts: {exc}"
                ) from exc
        if should_sleep:
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
    _validate_operation_name(operation_name)
    _validate_retry_config(
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
        max_status_failures=max_status_failures,
    )
    _validate_poll_interval(poll_interval_seconds)
    _validate_max_wait_seconds(max_wait_seconds)
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
    _validate_operation_name(operation_name)
    _validate_retry_config(
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
        max_status_failures=max_status_failures,
    )
    _validate_poll_interval(poll_interval_seconds)
    _validate_max_wait_seconds(max_wait_seconds)
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
