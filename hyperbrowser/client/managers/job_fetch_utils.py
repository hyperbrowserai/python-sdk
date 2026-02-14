from typing import Any, Awaitable, Callable, Optional, TypeVar

from ..polling import (
    build_fetch_operation_name,
    collect_paginated_results,
    collect_paginated_results_async,
    retry_operation,
    retry_operation_async,
)
from .polling_defaults import (
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLLING_RETRY_DELAY_SECONDS,
)

T = TypeVar("T")
R = TypeVar("R")


def retry_operation_with_defaults(
    *,
    operation_name: str,
    operation: Callable[[], T],
) -> T:
    return retry_operation(
        operation_name=operation_name,
        operation=operation,
        max_attempts=DEFAULT_POLLING_RETRY_ATTEMPTS,
        retry_delay_seconds=DEFAULT_POLLING_RETRY_DELAY_SECONDS,
    )


async def retry_operation_with_defaults_async(
    *,
    operation_name: str,
    operation: Callable[[], Awaitable[T]],
) -> T:
    return await retry_operation_async(
        operation_name=operation_name,
        operation=operation,
        max_attempts=DEFAULT_POLLING_RETRY_ATTEMPTS,
        retry_delay_seconds=DEFAULT_POLLING_RETRY_DELAY_SECONDS,
    )


def fetch_job_result_with_defaults(
    *,
    operation_name: str,
    fetch_result: Callable[[], T],
) -> T:
    return retry_operation_with_defaults(
        operation_name=build_fetch_operation_name(operation_name),
        operation=fetch_result,
    )


async def fetch_job_result_with_defaults_async(
    *,
    operation_name: str,
    fetch_result: Callable[[], Awaitable[T]],
) -> T:
    return await retry_operation_with_defaults_async(
        operation_name=build_fetch_operation_name(operation_name),
        operation=fetch_result,
    )


def read_page_current_batch(page_response: Any) -> int:
    return page_response.current_page_batch


def read_page_total_batches(page_response: Any) -> int:
    return page_response.total_page_batches


def collect_paginated_results_with_defaults(
    *,
    operation_name: str,
    get_next_page: Callable[[int], R],
    get_current_page_batch: Callable[[R], int],
    get_total_page_batches: Callable[[R], int],
    on_page_success: Callable[[R], None],
    max_wait_seconds: Optional[float],
) -> None:
    collect_paginated_results(
        operation_name=operation_name,
        get_next_page=get_next_page,
        get_current_page_batch=get_current_page_batch,
        get_total_page_batches=get_total_page_batches,
        on_page_success=on_page_success,
        max_wait_seconds=max_wait_seconds,
        max_attempts=DEFAULT_POLLING_RETRY_ATTEMPTS,
        retry_delay_seconds=DEFAULT_POLLING_RETRY_DELAY_SECONDS,
    )


async def collect_paginated_results_with_defaults_async(
    *,
    operation_name: str,
    get_next_page: Callable[[int], Awaitable[R]],
    get_current_page_batch: Callable[[R], int],
    get_total_page_batches: Callable[[R], int],
    on_page_success: Callable[[R], None],
    max_wait_seconds: Optional[float],
) -> None:
    await collect_paginated_results_async(
        operation_name=operation_name,
        get_next_page=get_next_page,
        get_current_page_batch=get_current_page_batch,
        get_total_page_batches=get_total_page_batches,
        on_page_success=on_page_success,
        max_wait_seconds=max_wait_seconds,
        max_attempts=DEFAULT_POLLING_RETRY_ATTEMPTS,
        retry_delay_seconds=DEFAULT_POLLING_RETRY_DELAY_SECONDS,
    )
