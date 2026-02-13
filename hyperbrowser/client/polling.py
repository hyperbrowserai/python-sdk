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
    return max_wait_seconds is not None and (
        time.monotonic() - start_time
    ) > max_wait_seconds


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
