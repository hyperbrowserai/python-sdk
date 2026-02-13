import asyncio
import math
from fractions import Fraction

import pytest

import hyperbrowser.client.polling as polling_helpers
from hyperbrowser.client.polling import (
    collect_paginated_results,
    collect_paginated_results_async,
    poll_until_terminal_status,
    poll_until_terminal_status_async,
    retry_operation,
    retry_operation_async,
    wait_for_job_result,
    wait_for_job_result_async,
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


def test_poll_until_terminal_status_allows_immediate_terminal_on_zero_max_wait():
    status = poll_until_terminal_status(
        operation_name="sync immediate zero wait",
        get_status=lambda: "completed",
        is_terminal_status=lambda value: value == "completed",
        poll_interval_seconds=0.0001,
        max_wait_seconds=0,
    )

    assert status == "completed"


def test_poll_until_terminal_status_zero_max_wait_times_out_after_first_check():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        return "running"

    with pytest.raises(
        HyperbrowserTimeoutError, match="Timed out waiting for sync zero wait timeout"
    ):
        poll_until_terminal_status(
            operation_name="sync zero wait timeout",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=0,
        )

    assert attempts["count"] == 1


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


def test_poll_until_terminal_status_rejects_awaitable_status_callback_result():
    async def async_get_status() -> str:
        return "completed"

    with pytest.raises(
        HyperbrowserError, match="get_status must return a non-awaitable result"
    ):
        poll_until_terminal_status(
            operation_name="sync poll awaitable callback",
            get_status=lambda: async_get_status(),  # type: ignore[return-value]
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=1,
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


def test_retry_operation_rejects_awaitable_operation_result():
    async def async_operation() -> str:
        return "ok"

    with pytest.raises(
        HyperbrowserError, match="operation must return a non-awaitable result"
    ):
        retry_operation(
            operation_name="sync retry awaitable callback",
            operation=lambda: async_operation(),  # type: ignore[return-value]
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


def test_retry_operation_async_rejects_non_awaitable_operation_result() -> None:
    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="operation must return an awaitable"
        ):
            await retry_operation_async(
                operation_name="invalid-async-retry-awaitable",
                operation=lambda: "ok",  # type: ignore[return-value]
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_async_poll_until_terminal_status_allows_immediate_terminal_on_zero_max_wait():
    async def run() -> None:
        status = await poll_until_terminal_status_async(
            operation_name="async immediate zero wait",
            get_status=lambda: asyncio.sleep(0, result="completed"),
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=0,
        )
        assert status == "completed"

    asyncio.run(run())


def test_async_poll_until_terminal_status_zero_max_wait_times_out_after_first_check():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            return "running"

        with pytest.raises(
            HyperbrowserTimeoutError,
            match="Timed out waiting for async zero wait timeout",
        ):
            await poll_until_terminal_status_async(
                operation_name="async zero wait timeout",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=0,
            )

        assert attempts["count"] == 1

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


def test_collect_paginated_results_rejects_awaitable_page_callback_result():
    async def async_get_page() -> dict:
        return {"current": 1, "total": 1, "items": []}

    with pytest.raises(
        HyperbrowserError, match="get_next_page must return a non-awaitable result"
    ):
        collect_paginated_results(
            operation_name="sync paginated awaitable page callback",
            get_next_page=lambda page: async_get_page(),  # type: ignore[return-value]
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_rejects_awaitable_on_page_success_result():
    with pytest.raises(
        HyperbrowserError, match="on_page_success must return a non-awaitable result"
    ):
        collect_paginated_results(
            operation_name="sync paginated awaitable success callback",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: asyncio.sleep(0),  # type: ignore[return-value]
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_allows_single_page_on_zero_max_wait():
    collected = []

    collect_paginated_results(
        operation_name="sync paginated zero wait",
        get_next_page=lambda page: {"current": 1, "total": 1, "items": ["a"]},
        get_current_page_batch=lambda response: response["current"],
        get_total_page_batches=lambda response: response["total"],
        on_page_success=lambda response: collected.extend(response["items"]),
        max_wait_seconds=0,
        max_attempts=2,
        retry_delay_seconds=0.0001,
    )

    assert collected == ["a"]


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


def test_collect_paginated_results_async_rejects_non_awaitable_page_callback_result():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="get_next_page must return an awaitable"
        ):
            await collect_paginated_results_async(
                operation_name="async paginated awaitable validation",
                get_next_page=lambda page: {"current": 1, "total": 1, "items": []},  # type: ignore[return-value]
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_collect_paginated_results_async_rejects_awaitable_on_page_success_result():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserError,
            match="on_page_success must return a non-awaitable result",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated awaitable success callback",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": 1, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: asyncio.sleep(0),  # type: ignore[return-value]
                max_wait_seconds=1.0,
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_collect_paginated_results_async_allows_single_page_on_zero_max_wait():
    async def run() -> None:
        collected = []

        await collect_paginated_results_async(
            operation_name="async paginated zero wait",
            get_next_page=lambda page: asyncio.sleep(
                0, result={"current": 1, "total": 1, "items": ["a"]}
            ),
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: collected.extend(response["items"]),
            max_wait_seconds=0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )

        assert collected == ["a"]

    asyncio.run(run())


def test_collect_paginated_results_does_not_sleep_after_last_page(monkeypatch):
    sleep_calls = []

    monkeypatch.setattr(
        polling_helpers.time, "sleep", lambda delay: sleep_calls.append(delay)
    )

    collect_paginated_results(
        operation_name="sync single-page",
        get_next_page=lambda page: {"current": 1, "total": 1, "items": ["a"]},
        get_current_page_batch=lambda response: response["current"],
        get_total_page_batches=lambda response: response["total"],
        on_page_success=lambda response: None,
        max_wait_seconds=1.0,
        max_attempts=2,
        retry_delay_seconds=0.5,
    )

    assert sleep_calls == []


def test_collect_paginated_results_async_does_not_sleep_after_last_page(monkeypatch):
    sleep_calls = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(polling_helpers.asyncio, "sleep", fake_sleep)

    async def run() -> None:
        async def get_next_page(page: int) -> dict:
            return {"current": 1, "total": 1, "items": ["a"]}

        await collect_paginated_results_async(
            operation_name="async single-page",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.5,
        )

    asyncio.run(run())

    assert sleep_calls == []


def test_collect_paginated_results_raises_after_page_failures():
    with pytest.raises(HyperbrowserError, match="Failed to fetch page batch 1"):
        collect_paginated_results(
            operation_name="sync paginated failure",
            get_next_page=lambda page: (_ for _ in ()).throw(ValueError("boom")),
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_raises_when_page_batch_stagnates():
    with pytest.raises(HyperbrowserPollingError, match="No pagination progress"):
        collect_paginated_results(
            operation_name="sync paginated stagnation",
            get_next_page=lambda page: {"current": 1, "total": 2, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_raises_on_invalid_page_batch_values():
    with pytest.raises(HyperbrowserPollingError, match="Invalid page batch state"):
        collect_paginated_results(
            operation_name="sync paginated invalid batches",
            get_next_page=lambda page: {"current": 3, "total": 2, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_raises_on_invalid_page_batch_types():
    with pytest.raises(
        HyperbrowserPollingError,
        match="Invalid current page batch for sync paginated invalid types",
    ):
        collect_paginated_results(
            operation_name="sync paginated invalid types",
            get_next_page=lambda page: {"current": "1", "total": 2, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_raises_on_boolean_page_batch_values():
    with pytest.raises(
        HyperbrowserPollingError,
        match="Invalid current page batch for sync paginated invalid bools",
    ):
        collect_paginated_results(
            operation_name="sync paginated invalid bools",
            get_next_page=lambda page: {"current": True, "total": 2, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=2,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_async_times_out():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserTimeoutError,
            match="Timed out fetching paginated results for async paginated timeout",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated timeout",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": 2, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=0.001,
                max_attempts=2,
                retry_delay_seconds=0.01,
            )

    asyncio.run(run())


def test_collect_paginated_results_async_raises_when_page_batch_stagnates():
    async def run() -> None:
        with pytest.raises(HyperbrowserPollingError, match="No pagination progress"):
            await collect_paginated_results_async(
                operation_name="async paginated stagnation",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": 2, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_collect_paginated_results_async_raises_on_invalid_page_batch_values():
    async def run() -> None:
        with pytest.raises(HyperbrowserPollingError, match="Invalid page batch state"):
            await collect_paginated_results_async(
                operation_name="async paginated invalid batches",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 3, "total": 2, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_collect_paginated_results_async_raises_on_invalid_page_batch_types():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserPollingError,
            match="Invalid total page batches for async paginated invalid types",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated invalid types",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": "2", "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_collect_paginated_results_async_raises_on_boolean_page_batch_values():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserPollingError,
            match="Invalid total page batches for async paginated invalid bools",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated invalid bools",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": False, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=2,
                retry_delay_seconds=0.0001,
            )

    asyncio.run(run())


def test_wait_for_job_result_returns_fetched_value():
    status_values = iter(["running", "completed"])

    result = wait_for_job_result(
        operation_name="sync wait helper",
        get_status=lambda: next(status_values),
        is_terminal_status=lambda value: value == "completed",
        fetch_result=lambda: {"ok": True},
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=2,
        fetch_max_attempts=2,
        fetch_retry_delay_seconds=0.0001,
    )

    assert result == {"ok": True}


def test_wait_for_job_result_async_returns_fetched_value():
    async def run() -> None:
        status_values = iter(["running", "completed"])

        result = await wait_for_job_result_async(
            operation_name="async wait helper",
            get_status=lambda: asyncio.sleep(0, result=next(status_values)),
            is_terminal_status=lambda value: value == "completed",
            fetch_result=lambda: asyncio.sleep(0, result={"ok": True}),
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=2,
            fetch_max_attempts=2,
            fetch_retry_delay_seconds=0.0001,
        )

        assert result == {"ok": True}

    asyncio.run(run())


def test_wait_for_job_result_validates_configuration():
    with pytest.raises(HyperbrowserError, match="max_attempts must be at least 1"):
        wait_for_job_result(
            operation_name="invalid-wait-config",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=lambda: {"ok": True},
            poll_interval_seconds=0.1,
            max_wait_seconds=1.0,
            max_status_failures=1,
            fetch_max_attempts=0,
            fetch_retry_delay_seconds=0.1,
        )


def test_wait_for_job_result_async_validates_configuration():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="poll_interval_seconds must be non-negative"
        ):
            await wait_for_job_result_async(
                operation_name="invalid-async-wait-config",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=lambda: asyncio.sleep(0, result={"ok": True}),
                poll_interval_seconds=-0.1,
                max_wait_seconds=1.0,
                max_status_failures=1,
                fetch_max_attempts=1,
                fetch_retry_delay_seconds=0.1,
            )

    asyncio.run(run())


def test_polling_helpers_validate_retry_and_interval_configuration():
    with pytest.raises(HyperbrowserError, match="max_attempts must be at least 1"):
        retry_operation(
            operation_name="invalid-retry",
            operation=lambda: "ok",
            max_attempts=0,
            retry_delay_seconds=0,
        )

    with pytest.raises(HyperbrowserError, match="operation_name must not be empty"):
        retry_operation(
            operation_name="   ",
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=0,
        )

    with pytest.raises(
        HyperbrowserError,
        match="operation_name must not contain leading or trailing whitespace",
    ):
        retry_operation(
            operation_name=" invalid-retry ",
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=0,
        )

    with pytest.raises(HyperbrowserError, match="operation_name must be a string"):
        retry_operation(
            operation_name=123,  # type: ignore[arg-type]
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=0,
        )

    with pytest.raises(
        HyperbrowserError, match="operation_name must not contain control characters"
    ):
        retry_operation(
            operation_name="invalid\nretry",
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=0,
        )

    with pytest.raises(
        HyperbrowserError, match="operation_name must be 200 characters or fewer"
    ):
        retry_operation(
            operation_name="x" * 201,
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=0,
        )

    with pytest.raises(HyperbrowserError, match="max_attempts must be an integer"):
        retry_operation(
            operation_name="invalid-retry-type",
            operation=lambda: "ok",
            max_attempts=1.5,  # type: ignore[arg-type]
            retry_delay_seconds=0,
        )

    with pytest.raises(
        HyperbrowserError, match="retry_delay_seconds must be non-negative"
    ):
        retry_operation(
            operation_name="invalid-delay",
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=-0.1,
        )

    with pytest.raises(
        HyperbrowserError, match="max_status_failures must be at least 1"
    ):
        poll_until_terminal_status(
            operation_name="invalid-status-failures",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.1,
            max_wait_seconds=1.0,
            max_status_failures=0,
        )

    with pytest.raises(
        HyperbrowserError, match="max_status_failures must be an integer"
    ):
        poll_until_terminal_status(
            operation_name="invalid-status-failures-type",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.1,
            max_wait_seconds=1.0,
            max_status_failures=1.5,  # type: ignore[arg-type]
        )

    with pytest.raises(
        HyperbrowserError, match="poll_interval_seconds must be non-negative"
    ):
        poll_until_terminal_status(
            operation_name="invalid-poll-interval",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=-0.1,
            max_wait_seconds=1.0,
        )

    with pytest.raises(
        HyperbrowserError, match="poll_interval_seconds must be a number"
    ):
        poll_until_terminal_status(
            operation_name="invalid-poll-interval-type",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds="0.1",  # type: ignore[arg-type]
            max_wait_seconds=1.0,
        )

    with pytest.raises(
        HyperbrowserError, match="is_terminal_status must return a boolean"
    ):
        poll_until_terminal_status(
            operation_name="invalid-terminal-callback",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: "yes",  # type: ignore[return-value]
            poll_interval_seconds=0.0,
            max_wait_seconds=1.0,
        )
    with pytest.raises(HyperbrowserError, match="get_status must return a string"):
        poll_until_terminal_status(
            operation_name="invalid-status-value",
            get_status=lambda: 123,  # type: ignore[return-value]
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0,
            max_wait_seconds=1.0,
        )

    with pytest.raises(
        HyperbrowserError, match="max_wait_seconds must be non-negative"
    ):
        collect_paginated_results(
            operation_name="invalid-max-wait",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=-1.0,
            max_attempts=1,
            retry_delay_seconds=0.0,
        )

    with pytest.raises(HyperbrowserError, match="max_wait_seconds must be a number"):
        collect_paginated_results(
            operation_name="invalid-max-wait-type",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds="1",  # type: ignore[arg-type]
            max_attempts=1,
            retry_delay_seconds=0.0,
        )

    with pytest.raises(HyperbrowserError, match="retry_delay_seconds must be finite"):
        retry_operation(
            operation_name="invalid-retry-delay-finite",
            operation=lambda: "ok",
            max_attempts=1,
            retry_delay_seconds=math.inf,
        )

    with pytest.raises(HyperbrowserError, match="poll_interval_seconds must be finite"):
        poll_until_terminal_status(
            operation_name="invalid-poll-interval-finite",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=math.nan,
            max_wait_seconds=1.0,
        )

    with pytest.raises(HyperbrowserError, match="max_wait_seconds must be finite"):
        collect_paginated_results(
            operation_name="invalid-max-wait-finite",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=math.inf,
            max_attempts=1,
            retry_delay_seconds=0.0,
        )

    with pytest.raises(HyperbrowserError, match="poll_interval_seconds must be finite"):
        poll_until_terminal_status(
            operation_name="invalid-poll-interval-overflowing-real",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=Fraction(10**1000, 1),  # type: ignore[arg-type]
            max_wait_seconds=1.0,
        )

    async def validate_async_operation_name() -> None:
        with pytest.raises(HyperbrowserError, match="operation_name must not be empty"):
            await poll_until_terminal_status_async(
                operation_name="   ",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.1,
                max_wait_seconds=1.0,
            )
        with pytest.raises(
            HyperbrowserError,
            match="operation_name must not contain leading or trailing whitespace",
        ):
            await poll_until_terminal_status_async(
                operation_name=" invalid-async ",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.1,
                max_wait_seconds=1.0,
            )
        with pytest.raises(
            HyperbrowserError,
            match="operation_name must not contain control characters",
        ):
            await poll_until_terminal_status_async(
                operation_name="invalid\tasync",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.1,
                max_wait_seconds=1.0,
            )
        with pytest.raises(
            HyperbrowserError, match="is_terminal_status must return a boolean"
        ):
            await poll_until_terminal_status_async(
                operation_name="invalid-terminal-callback-async",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: "yes",  # type: ignore[return-value]
                poll_interval_seconds=0.0,
                max_wait_seconds=1.0,
            )
        with pytest.raises(HyperbrowserError, match="get_status must return a string"):
            await poll_until_terminal_status_async(
                operation_name="invalid-status-value-async",
                get_status=lambda: asyncio.sleep(0, result=123),  # type: ignore[arg-type]
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0,
                max_wait_seconds=1.0,
            )
        with pytest.raises(
            HyperbrowserError, match="get_status must return an awaitable"
        ):
            await poll_until_terminal_status_async(
                operation_name="invalid-status-awaitable-async",
                get_status=lambda: "completed",  # type: ignore[return-value]
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0,
                max_wait_seconds=1.0,
            )
        with pytest.raises(
            HyperbrowserError, match="operation_name must be 200 characters or fewer"
        ):
            await poll_until_terminal_status_async(
                operation_name="x" * 201,
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.1,
                max_wait_seconds=1.0,
            )

    asyncio.run(validate_async_operation_name())
