import asyncio
import inspect
import math
from numbers import Real
import time
from typing import Awaitable, Callable, Optional, TypeVar

from hyperbrowser.exceptions import (
    HyperbrowserError,
    HyperbrowserPollingError,
    HyperbrowserTimeoutError,
)

T = TypeVar("T")
_MAX_OPERATION_NAME_LENGTH = 200


class _NonRetryablePollingError(HyperbrowserError):
    pass


def _validate_non_negative_real(value: float, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise HyperbrowserError(f"{field_name} must be a number")
    try:
        is_finite = math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        is_finite = False
    if not is_finite:
        raise HyperbrowserError(f"{field_name} must be finite")
    if value < 0:
        raise HyperbrowserError(f"{field_name} must be non-negative")


def _validate_operation_name(operation_name: str) -> None:
    if not isinstance(operation_name, str):
        raise HyperbrowserError("operation_name must be a string")
    if not operation_name.strip():
        raise HyperbrowserError("operation_name must not be empty")
    if operation_name != operation_name.strip():
        raise HyperbrowserError(
            "operation_name must not contain leading or trailing whitespace"
        )
    if len(operation_name) > _MAX_OPERATION_NAME_LENGTH:
        raise HyperbrowserError(
            f"operation_name must be {_MAX_OPERATION_NAME_LENGTH} characters or fewer"
        )
    if any(
        ord(character) < 32 or ord(character) == 127 for character in operation_name
    ):
        raise HyperbrowserError("operation_name must not contain control characters")


def _ensure_boolean_terminal_result(result: object, *, operation_name: str) -> bool:
    _ensure_non_awaitable(
        result, callback_name="is_terminal_status", operation_name=operation_name
    )
    if not isinstance(result, bool):
        raise _NonRetryablePollingError(
            f"is_terminal_status must return a boolean for {operation_name}"
        )
    return result


def _ensure_status_string(status: object, *, operation_name: str) -> str:
    _ensure_non_awaitable(
        status, callback_name="get_status", operation_name=operation_name
    )
    if not isinstance(status, str):
        raise _NonRetryablePollingError(
            f"get_status must return a string for {operation_name}"
        )
    return status


def _ensure_awaitable(
    result: object, *, callback_name: str, operation_name: str
) -> Awaitable[object]:
    if not inspect.isawaitable(result):
        raise _NonRetryablePollingError(
            f"{callback_name} must return an awaitable for {operation_name}"
        )
    return result


def _ensure_non_awaitable(
    result: object, *, callback_name: str, operation_name: str
) -> None:
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result):
            result.close()
        raise _NonRetryablePollingError(
            f"{callback_name} must return a non-awaitable result for {operation_name}"
        )


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
    _validate_non_negative_real(retry_delay_seconds, field_name="retry_delay_seconds")
    if max_status_failures is not None:
        if isinstance(max_status_failures, bool) or not isinstance(
            max_status_failures, int
        ):
            raise HyperbrowserError("max_status_failures must be an integer")
        if max_status_failures < 1:
            raise HyperbrowserError("max_status_failures must be at least 1")


def _validate_poll_interval(poll_interval_seconds: float) -> None:
    _validate_non_negative_real(
        poll_interval_seconds, field_name="poll_interval_seconds"
    )


def _validate_max_wait_seconds(max_wait_seconds: Optional[float]) -> None:
    if max_wait_seconds is None:
        return
    _validate_non_negative_real(max_wait_seconds, field_name="max_wait_seconds")


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
        try:
            status = get_status()
            failures = 0
        except Exception as exc:
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    f"Failed to poll {operation_name} after {max_status_failures} attempts: {exc}"
                ) from exc
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
                )
            time.sleep(poll_interval_seconds)
            continue

        status = _ensure_status_string(status, operation_name=operation_name)
        if _ensure_boolean_terminal_result(
            is_terminal_status(status), operation_name=operation_name
        ):
            return status
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
            )
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
            operation_result = operation()
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: {exc}"
                ) from exc
            time.sleep(retry_delay_seconds)
            continue

        _ensure_non_awaitable(
            operation_result,
            callback_name="operation",
            operation_name=operation_name,
        )
        return operation_result


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
        try:
            status_result = get_status()
        except Exception as exc:
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    f"Failed to poll {operation_name} after {max_status_failures} attempts: {exc}"
                ) from exc
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
                )
            await asyncio.sleep(poll_interval_seconds)
            continue

        status_awaitable = _ensure_awaitable(
            status_result, callback_name="get_status", operation_name=operation_name
        )
        try:
            status = await status_awaitable
            failures = 0
        except Exception as exc:
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    f"Failed to poll {operation_name} after {max_status_failures} attempts: {exc}"
                ) from exc
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
                )
            await asyncio.sleep(poll_interval_seconds)
            continue

        status = _ensure_status_string(status, operation_name=operation_name)
        if _ensure_boolean_terminal_result(
            is_terminal_status(status), operation_name=operation_name
        ):
            return status
        if has_exceeded_max_wait(start_time, max_wait_seconds):
            raise HyperbrowserTimeoutError(
                f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
            )
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
            operation_result = operation()
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: {exc}"
                ) from exc
            await asyncio.sleep(retry_delay_seconds)
            continue

        operation_awaitable = _ensure_awaitable(
            operation_result,
            callback_name="operation",
            operation_name=operation_name,
        )

        try:
            return await operation_awaitable
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
        should_sleep = True
        try:
            previous_page_batch = current_page_batch
            page_response = get_next_page(current_page_batch + 1)
            _ensure_non_awaitable(
                page_response,
                callback_name="get_next_page",
                operation_name=operation_name,
            )
            callback_result = on_page_success(page_response)
            _ensure_non_awaitable(
                callback_result,
                callback_name="on_page_success",
                operation_name=operation_name,
            )
            current_page_batch = get_current_page_batch(page_response)
            _ensure_non_awaitable(
                current_page_batch,
                callback_name="get_current_page_batch",
                operation_name=operation_name,
            )
            total_page_batches = get_total_page_batches(page_response)
            _ensure_non_awaitable(
                total_page_batches,
                callback_name="get_total_page_batches",
                operation_name=operation_name,
            )
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
        except _NonRetryablePollingError:
            raise
        except HyperbrowserPollingError:
            raise
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"Failed to fetch page batch {current_page_batch + 1} for {operation_name} after {max_attempts} attempts: {exc}"
                ) from exc
        if should_sleep:
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out fetching paginated results for {operation_name} after {max_wait_seconds} seconds"
                )
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
        should_sleep = True
        try:
            previous_page_batch = current_page_batch
            page_result = get_next_page(current_page_batch + 1)
            page_awaitable = _ensure_awaitable(
                page_result,
                callback_name="get_next_page",
                operation_name=operation_name,
            )
            page_response = await page_awaitable
            callback_result = on_page_success(page_response)
            _ensure_non_awaitable(
                callback_result,
                callback_name="on_page_success",
                operation_name=operation_name,
            )
            current_page_batch = get_current_page_batch(page_response)
            _ensure_non_awaitable(
                current_page_batch,
                callback_name="get_current_page_batch",
                operation_name=operation_name,
            )
            total_page_batches = get_total_page_batches(page_response)
            _ensure_non_awaitable(
                total_page_batches,
                callback_name="get_total_page_batches",
                operation_name=operation_name,
            )
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
        except _NonRetryablePollingError:
            raise
        except HyperbrowserPollingError:
            raise
        except Exception as exc:
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"Failed to fetch page batch {current_page_batch + 1} for {operation_name} after {max_attempts} attempts: {exc}"
                ) from exc
        if should_sleep:
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out fetching paginated results for {operation_name} after {max_wait_seconds} seconds"
                )
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
