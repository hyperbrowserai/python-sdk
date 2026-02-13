import asyncio

import pytest

from hyperbrowser.client.polling import (
    collect_paginated_results,
    collect_paginated_results_async,
    poll_until_terminal_status,
    poll_until_terminal_status_async,
    retry_operation,
    retry_operation_async,
)
from hyperbrowser.exceptions import (
    HyperbrowserError,
    HyperbrowserPollingError,
    HyperbrowserTimeoutError,
)


def test_poll_until_terminal_status_returns_terminal_value():
    status_values = iter(["pending", "running", "completed"])

    status = poll_until_terminal_status(
        operation_name="sync poll",
        get_status=lambda: next(status_values),
        is_terminal_status=lambda value: value in {"completed", "failed"},
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
    )

    assert status == "completed"


def test_poll_until_terminal_status_times_out():
    with pytest.raises(
        HyperbrowserTimeoutError, match="Timed out waiting for sync timeout"
    ):
        poll_until_terminal_status(
            operation_name="sync timeout",
            get_status=lambda: "running",
            is_terminal_status=lambda value: value in {"completed", "failed"},
            poll_interval_seconds=0.0001,
            max_wait_seconds=0.01,
        )


def test_poll_until_terminal_status_retries_transient_status_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("temporary")
        return "completed"

    status = poll_until_terminal_status(
        operation_name="sync poll retries",
        get_status=get_status,
        is_terminal_status=lambda value: value in {"completed", "failed"},
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
    )

    assert status == "completed"


def test_poll_until_terminal_status_raises_after_status_failures():
    with pytest.raises(
        HyperbrowserPollingError, match="Failed to poll sync poll failure"
    ):
        poll_until_terminal_status(
            operation_name="sync poll failure",
            get_status=lambda: (_ for _ in ()).throw(ValueError("always")),
            is_terminal_status=lambda value: value in {"completed", "failed"},
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=2,
        )


def test_retry_operation_retries_and_returns_value():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("transient")
        return "ok"

    result = retry_operation(
        operation_name="sync retry",
        operation=operation,
        max_attempts=3,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"


def test_retry_operation_raises_after_max_attempts():
    with pytest.raises(HyperbrowserError, match="sync retry failure"):
        retry_operation(
            operation_name="sync retry failure",
            operation=lambda: (_ for _ in ()).throw(ValueError("always")),
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_async_polling_and_retry_helpers():
    async def run() -> None:
        status_values = iter(["pending", "completed"])

        status = await poll_until_terminal_status_async(
            operation_name="async poll",
            get_status=lambda: asyncio.sleep(0, result=next(status_values)),
            is_terminal_status=lambda value: value in {"completed", "failed"},
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
        )
        assert status == "completed"

        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ValueError("transient")
            return "ok"

        result = await retry_operation_async(
            operation_name="async retry",
            operation=operation,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )
        assert result == "ok"

    asyncio.run(run())


def test_async_poll_until_terminal_status_retries_transient_status_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ValueError("temporary")
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll retries",
            get_status=get_status,
            is_terminal_status=lambda value: value in {"completed", "failed"},
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
        )
        assert status == "completed"

    asyncio.run(run())


def test_async_poll_until_terminal_status_raises_after_status_failures():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserPollingError, match="Failed to poll async poll failure"
        ):
            await poll_until_terminal_status_async(
                operation_name="async poll failure",
                get_status=lambda: (_ for _ in ()).throw(ValueError("always")),
                is_terminal_status=lambda value: value in {"completed", "failed"},
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=2,
            )

    asyncio.run(run())


def test_collect_paginated_results_collects_all_pages():
    page_map = {
        1: {"current": 1, "total": 2, "items": ["a"]},
        2: {"current": 2, "total": 2, "items": ["b"]},
    }
    collected = []

    collect_paginated_results(
        operation_name="sync paginated",
        get_next_page=lambda page: page_map[page],
        get_current_page_batch=lambda response: response["current"],
        get_total_page_batches=lambda response: response["total"],
        on_page_success=lambda response: collected.extend(response["items"]),
        max_wait_seconds=1.0,
        max_attempts=2,
        retry_delay_seconds=0.0001,
    )

    assert collected == ["a", "b"]


def test_collect_paginated_results_async_collects_all_pages():
    async def run() -> None:
        page_map = {
            1: {"current": 1, "total": 2, "items": ["a"]},
            2: {"current": 2, "total": 2, "items": ["b"]},
        }
        collected = []

        await collect_paginated_results_async(
            operation_name="async paginated",
            get_next_page=lambda page: asyncio.sleep(0, result=page_map[page]),
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: collected.extend(response["items"]),
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )

        assert collected == ["a", "b"]

    asyncio.run(run())
