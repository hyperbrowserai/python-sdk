import asyncio
from concurrent.futures import BrokenExecutor as ConcurrentBrokenExecutor
from concurrent.futures import CancelledError as ConcurrentCancelledError
from concurrent.futures import InvalidStateError as ConcurrentInvalidStateError
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


def test_poll_until_terminal_status_does_not_retry_non_retryable_client_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise HyperbrowserError("client failure", status_code=400)

    with pytest.raises(HyperbrowserError, match="client failure"):
        poll_until_terminal_status(
            operation_name="sync poll client error",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_numeric_string_client_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise HyperbrowserError("client failure", status_code="400")  # type: ignore[arg-type]

    with pytest.raises(HyperbrowserError, match="client failure"):
        poll_until_terminal_status(
            operation_name="sync poll numeric-string client error",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_retries_overlong_numeric_status_codes():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError(
                "oversized status metadata",
                status_code="4000000000000",  # type: ignore[arg-type]
            )
        return "completed"

    status = poll_until_terminal_status(
        operation_name="sync poll oversized numeric status retries",
        get_status=get_status,
        is_terminal_status=lambda value: value == "completed",
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
    )

    assert status == "completed"
    assert attempts["count"] == 3


def test_poll_until_terminal_status_does_not_retry_stop_iteration_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise StopIteration("callback exhausted")

    with pytest.raises(StopIteration, match="callback exhausted"):
        poll_until_terminal_status(
            operation_name="sync poll stop-iteration passthrough",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_generator_reentrancy_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise ValueError("generator already executing")

    with pytest.raises(ValueError, match="generator already executing"):
        poll_until_terminal_status(
            operation_name="sync poll generator-reentrancy passthrough",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_timeout_or_polling_errors():
    timeout_attempts = {"count": 0}

    def get_status_timeout() -> str:
        timeout_attempts["count"] += 1
        raise HyperbrowserTimeoutError("timed out internally")

    with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
        poll_until_terminal_status(
            operation_name="sync poll timeout passthrough",
            get_status=get_status_timeout,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert timeout_attempts["count"] == 1

    polling_attempts = {"count": 0}

    def get_status_polling_error() -> str:
        polling_attempts["count"] += 1
        raise HyperbrowserPollingError("upstream polling failure")

    with pytest.raises(HyperbrowserPollingError, match="upstream polling failure"):
        poll_until_terminal_status(
            operation_name="sync poll polling-error passthrough",
            get_status=get_status_polling_error,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert polling_attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_concurrent_cancelled_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise ConcurrentCancelledError()

    with pytest.raises(ConcurrentCancelledError):
        poll_until_terminal_status(
            operation_name="sync poll concurrent-cancelled passthrough",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_broken_executor_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise ConcurrentBrokenExecutor("executor is broken")

    with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
        poll_until_terminal_status(
            operation_name="sync poll broken-executor passthrough",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_invalid_state_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise asyncio.InvalidStateError("invalid async state")

    with pytest.raises(asyncio.InvalidStateError, match="invalid async state"):
        poll_until_terminal_status(
            operation_name="sync poll invalid-state passthrough",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_does_not_retry_executor_shutdown_runtime_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        raise RuntimeError("cannot schedule new futures after shutdown")

    with pytest.raises(
        RuntimeError, match="cannot schedule new futures after shutdown"
    ):
        poll_until_terminal_status(
            operation_name="sync poll executor-shutdown passthrough",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_retries_rate_limit_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("rate limited", status_code=429)
        return "completed"

    status = poll_until_terminal_status(
        operation_name="sync poll rate limit retries",
        get_status=get_status,
        is_terminal_status=lambda value: value == "completed",
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
    )

    assert status == "completed"
    assert attempts["count"] == 3


def test_poll_until_terminal_status_retries_request_timeout_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("request timeout", status_code=408)
        return "completed"

    status = poll_until_terminal_status(
        operation_name="sync poll request-timeout retries",
        get_status=get_status,
        is_terminal_status=lambda value: value == "completed",
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
    )

    assert status == "completed"
    assert attempts["count"] == 3


def test_poll_until_terminal_status_async_retries_rate_limit_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("rate limited", status_code=429)
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll rate limit retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_retries_request_timeout_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("request timeout", status_code=408)
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll request-timeout retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_handles_non_integer_status_codes_as_retryable():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "malformed status code",
                    status_code="invalid-status",  # type: ignore[arg-type]
                )
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll malformed status code retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_handles_unicode_digit_like_status_codes_as_retryable():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "unicode digit-like status code",
                    status_code="²",  # type: ignore[arg-type]
                )
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll unicode digit-like status retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_handles_non_ascii_numeric_status_codes_as_retryable():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "non-ascii numeric status code",
                    status_code="٤٢٩",  # type: ignore[arg-type]
                )
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll non-ascii numeric status retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_handles_non_ascii_byte_status_codes_as_retryable():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "non-ascii byte status code",
                    status_code=b"\xff",  # type: ignore[arg-type]
                )
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll non-ascii byte status retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_retries_server_errors():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("server failure", status_code=503)
        return "completed"

    status = poll_until_terminal_status(
        operation_name="sync poll server error retries",
        get_status=get_status,
        is_terminal_status=lambda value: value == "completed",
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
    )

    assert status == "completed"
    assert attempts["count"] == 3


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

    attempts = {"count": 0}

    def get_status() -> object:
        attempts["count"] += 1
        return async_get_status()

    with pytest.raises(
        HyperbrowserError, match="get_status must return a non-awaitable result"
    ):
        poll_until_terminal_status(
            operation_name="sync poll awaitable callback",
            get_status=get_status,  # type: ignore[arg-type]
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_cancels_future_status_callback_results():
    loop = asyncio.new_event_loop()
    try:
        status_future = loop.create_future()

        with pytest.raises(
            HyperbrowserError, match="get_status must return a non-awaitable result"
        ):
            poll_until_terminal_status(
                operation_name="sync poll status future",
                get_status=lambda: status_future,  # type: ignore[return-value]
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert status_future.cancelled()
    finally:
        loop.close()


def test_poll_until_terminal_status_fails_fast_when_terminal_callback_raises():
    attempts = {"count": 0}

    def get_status() -> str:
        attempts["count"] += 1
        return "completed"

    with pytest.raises(HyperbrowserError, match="is_terminal_status failed"):
        poll_until_terminal_status(
            operation_name="sync terminal callback exception",
            get_status=get_status,
            is_terminal_status=lambda value: (_ for _ in ()).throw(ValueError("boom")),
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_cancels_future_terminal_callback_results():
    loop = asyncio.new_event_loop()
    try:
        callback_future = loop.create_future()

        with pytest.raises(
            HyperbrowserError,
            match="is_terminal_status must return a non-awaitable result",
        ):
            poll_until_terminal_status(
                operation_name="sync terminal callback future",
                get_status=lambda: "completed",
                is_terminal_status=lambda value: callback_future,  # type: ignore[return-value]
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert callback_future.cancelled()
    finally:
        loop.close()


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


def test_retry_operation_does_not_retry_non_retryable_client_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise HyperbrowserError("client failure", status_code=404)

    with pytest.raises(HyperbrowserError, match="client failure"):
        retry_operation(
            operation_name="sync retry client error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_retries_numeric_string_rate_limit_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError(
                "rate limited",
                status_code=" 429 ",  # type: ignore[arg-type]
            )
        return "ok"

    result = retry_operation(
        operation_name="sync retry numeric-string rate limit",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_does_not_retry_numeric_bytes_client_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise HyperbrowserError(
            "client failure",
            status_code=b"400",  # type: ignore[arg-type]
        )

    with pytest.raises(HyperbrowserError, match="client failure"):
        retry_operation(
            operation_name="sync retry numeric-bytes client error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_stop_iteration_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise StopIteration("callback exhausted")

    with pytest.raises(StopIteration, match="callback exhausted"):
        retry_operation(
            operation_name="sync retry stop-iteration passthrough",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_generator_reentrancy_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise ValueError("generator already executing")

    with pytest.raises(ValueError, match="generator already executing"):
        retry_operation(
            operation_name="sync retry generator-reentrancy passthrough",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_timeout_or_polling_errors():
    timeout_attempts = {"count": 0}

    def timeout_operation() -> str:
        timeout_attempts["count"] += 1
        raise HyperbrowserTimeoutError("timed out internally")

    with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
        retry_operation(
            operation_name="sync retry timeout passthrough",
            operation=timeout_operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert timeout_attempts["count"] == 1

    polling_attempts = {"count": 0}

    def polling_error_operation() -> str:
        polling_attempts["count"] += 1
        raise HyperbrowserPollingError("upstream polling failure")

    with pytest.raises(HyperbrowserPollingError, match="upstream polling failure"):
        retry_operation(
            operation_name="sync retry polling-error passthrough",
            operation=polling_error_operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert polling_attempts["count"] == 1


def test_retry_operation_does_not_retry_concurrent_cancelled_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise ConcurrentCancelledError()

    with pytest.raises(ConcurrentCancelledError):
        retry_operation(
            operation_name="sync retry concurrent-cancelled passthrough",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_broken_executor_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise ConcurrentBrokenExecutor("executor is broken")

    with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
        retry_operation(
            operation_name="sync retry broken-executor passthrough",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_invalid_state_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise ConcurrentInvalidStateError("invalid executor state")

    with pytest.raises(ConcurrentInvalidStateError, match="invalid executor state"):
        retry_operation(
            operation_name="sync retry invalid-state passthrough",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_retries_server_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("server failure", status_code=502)
        return "ok"

    result = retry_operation(
        operation_name="sync retry server error",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_retries_rate_limit_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("rate limited", status_code=429)
        return "ok"

    result = retry_operation(
        operation_name="sync retry rate limit error",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_retries_request_timeout_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("request timeout", status_code=408)
        return "ok"

    result = retry_operation(
        operation_name="sync retry request-timeout error",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_handles_non_integer_status_codes_as_retryable():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError(
                "malformed status code",
                status_code="invalid-status",  # type: ignore[arg-type]
            )
        return "ok"

    result = retry_operation(
        operation_name="sync retry malformed status code",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_handles_unicode_digit_like_status_codes_as_retryable():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError(
                "unicode digit-like status code",
                status_code="²",  # type: ignore[arg-type]
            )
        return "ok"

    result = retry_operation(
        operation_name="sync retry unicode digit-like status code",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_handles_non_ascii_numeric_status_codes_as_retryable():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError(
                "non-ascii numeric status code",
                status_code="４２９",  # type: ignore[arg-type]
            )
        return "ok"

    result = retry_operation(
        operation_name="sync retry non-ascii numeric status code",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_handles_non_ascii_byte_status_codes_as_retryable():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError(
                "non-ascii byte status code",
                status_code=b"\xfe",  # type: ignore[arg-type]
            )
        return "ok"

    result = retry_operation(
        operation_name="sync retry non-ascii byte status code",
        operation=operation,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_operation_rejects_awaitable_operation_result():
    async def async_operation() -> str:
        return "ok"

    attempts = {"count": 0}

    def operation() -> object:
        attempts["count"] += 1
        return async_operation()

    with pytest.raises(
        HyperbrowserError, match="operation must return a non-awaitable result"
    ):
        retry_operation(
            operation_name="sync retry awaitable callback",
            operation=operation,  # type: ignore[arg-type]
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_cancels_future_operation_results():
    loop = asyncio.new_event_loop()
    try:
        operation_future = loop.create_future()

        with pytest.raises(
            HyperbrowserError, match="operation must return a non-awaitable result"
        ):
            retry_operation(
                operation_name="sync retry future callback",
                operation=lambda: operation_future,  # type: ignore[return-value]
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert operation_future.cancelled()
    finally:
        loop.close()


def test_retry_operation_consumes_completed_future_exceptions():
    loop = asyncio.new_event_loop()
    try:
        completed_future = loop.create_future()
        completed_future.set_exception(RuntimeError("boom"))

        with pytest.raises(
            HyperbrowserError, match="operation must return a non-awaitable result"
        ):
            retry_operation(
                operation_name="sync retry completed-future callback",
                operation=lambda: completed_future,  # type: ignore[return-value]
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert getattr(completed_future, "_log_traceback", False) is False
    finally:
        loop.close()


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


def test_poll_until_terminal_status_async_does_not_retry_non_retryable_client_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise HyperbrowserError("client failure", status_code=400)

        with pytest.raises(HyperbrowserError, match="client failure"):
            await poll_until_terminal_status_async(
                operation_name="async poll client error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_numeric_string_client_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise HyperbrowserError(
                "client failure",
                status_code="404",  # type: ignore[arg-type]
            )

        with pytest.raises(HyperbrowserError, match="client failure"):
            await poll_until_terminal_status_async(
                operation_name="async poll numeric-string client error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_retries_overlong_numeric_status_codes():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "oversized status metadata",
                    status_code="4000000000000",  # type: ignore[arg-type]
                )
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll oversized numeric status retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_stop_async_iteration_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise StopAsyncIteration("callback exhausted")

        with pytest.raises(StopAsyncIteration, match="callback exhausted"):
            await poll_until_terminal_status_async(
                operation_name="async poll stop-async-iteration passthrough",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_generator_reentrancy_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise ValueError("generator already executing")

        with pytest.raises(ValueError, match="generator already executing"):
            await poll_until_terminal_status_async(
                operation_name="async poll generator-reentrancy passthrough",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_timeout_or_polling_errors():
    async def run() -> None:
        timeout_attempts = {"count": 0}

        async def get_status_timeout() -> str:
            timeout_attempts["count"] += 1
            raise HyperbrowserTimeoutError("timed out internally")

        with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
            await poll_until_terminal_status_async(
                operation_name="async poll timeout passthrough",
                get_status=get_status_timeout,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert timeout_attempts["count"] == 1

        polling_attempts = {"count": 0}

        async def get_status_polling_error() -> str:
            polling_attempts["count"] += 1
            raise HyperbrowserPollingError("upstream polling failure")

        with pytest.raises(HyperbrowserPollingError, match="upstream polling failure"):
            await poll_until_terminal_status_async(
                operation_name="async poll polling-error passthrough",
                get_status=get_status_polling_error,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert polling_attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_concurrent_cancelled_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise ConcurrentCancelledError()

        with pytest.raises(ConcurrentCancelledError):
            await poll_until_terminal_status_async(
                operation_name="async poll concurrent-cancelled passthrough",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_broken_executor_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise ConcurrentBrokenExecutor("executor is broken")

        with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
            await poll_until_terminal_status_async(
                operation_name="async poll broken-executor passthrough",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_invalid_state_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise asyncio.InvalidStateError("invalid async state")

        with pytest.raises(asyncio.InvalidStateError, match="invalid async state"):
            await poll_until_terminal_status_async(
                operation_name="async poll invalid-state passthrough",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_retries_server_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("server failure", status_code=503)
            return "completed"

        status = await poll_until_terminal_status_async(
            operation_name="async poll server error retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
        )

        assert status == "completed"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_fails_fast_when_terminal_callback_raises():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            return "completed"

        with pytest.raises(HyperbrowserError, match="is_terminal_status failed"):
            await poll_until_terminal_status_async(
                operation_name="async terminal callback exception",
                get_status=get_status,
                is_terminal_status=lambda value: (_ for _ in ()).throw(
                    ValueError("boom")
                ),
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_non_retryable_client_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise HyperbrowserError("client failure", status_code=400)

        with pytest.raises(HyperbrowserError, match="client failure"):
            await retry_operation_async(
                operation_name="async retry client error",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_retries_numeric_string_rate_limit_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "rate limited",
                    status_code="429",  # type: ignore[arg-type]
                )
            return "ok"

        result = await retry_operation_async(
            operation_name="async retry numeric-string rate limit",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert result == "ok"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_retry_operation_async_retries_numeric_bytes_rate_limit_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError(
                    "rate limited",
                    status_code=b"429",  # type: ignore[arg-type]
                )
            return "ok"

        result = await retry_operation_async(
            operation_name="async retry numeric-bytes rate limit",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert result == "ok"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_stop_async_iteration_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise StopAsyncIteration("callback exhausted")

        with pytest.raises(StopAsyncIteration, match="callback exhausted"):
            await retry_operation_async(
                operation_name="async retry stop-async-iteration passthrough",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_generator_reentrancy_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise ValueError("generator already executing")

        with pytest.raises(ValueError, match="generator already executing"):
            await retry_operation_async(
                operation_name="async retry generator-reentrancy passthrough",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_timeout_or_polling_errors():
    async def run() -> None:
        timeout_attempts = {"count": 0}

        async def timeout_operation() -> str:
            timeout_attempts["count"] += 1
            raise HyperbrowserTimeoutError("timed out internally")

        with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
            await retry_operation_async(
                operation_name="async retry timeout passthrough",
                operation=timeout_operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert timeout_attempts["count"] == 1

        polling_attempts = {"count": 0}

        async def polling_error_operation() -> str:
            polling_attempts["count"] += 1
            raise HyperbrowserPollingError("upstream polling failure")

        with pytest.raises(HyperbrowserPollingError, match="upstream polling failure"):
            await retry_operation_async(
                operation_name="async retry polling-error passthrough",
                operation=polling_error_operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert polling_attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_concurrent_cancelled_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise ConcurrentCancelledError()

        with pytest.raises(ConcurrentCancelledError):
            await retry_operation_async(
                operation_name="async retry concurrent-cancelled passthrough",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_broken_executor_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise ConcurrentBrokenExecutor("executor is broken")

        with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
            await retry_operation_async(
                operation_name="async retry broken-executor passthrough",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_invalid_state_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise ConcurrentInvalidStateError("invalid executor state")

        with pytest.raises(ConcurrentInvalidStateError, match="invalid executor state"):
            await retry_operation_async(
                operation_name="async retry invalid-state passthrough",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_executor_shutdown_runtime_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            raise RuntimeError("cannot schedule new futures after shutdown")

        with pytest.raises(
            RuntimeError, match="cannot schedule new futures after shutdown"
        ):
            await retry_operation_async(
                operation_name="async retry executor-shutdown passthrough",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_async_retries_server_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("server failure", status_code=503)
            return "ok"

        result = await retry_operation_async(
            operation_name="async retry server error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert result == "ok"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_retry_operation_async_retries_rate_limit_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("rate limited", status_code=429)
            return "ok"

        result = await retry_operation_async(
            operation_name="async retry rate limit error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert result == "ok"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_retry_operation_async_retries_request_timeout_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def operation() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("request timeout", status_code=408)
            return "ok"

        result = await retry_operation_async(
            operation_name="async retry request-timeout error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert result == "ok"
        assert attempts["count"] == 3

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_reused_coroutines():
    async def run() -> None:
        attempts = {"count": 0}
        shared_status_coroutine = asyncio.sleep(0, result="running")

        async def get_status() -> str:
            attempts["count"] += 1
            return await shared_status_coroutine

        with pytest.raises(
            RuntimeError, match="cannot reuse already awaited coroutine"
        ):
            await poll_until_terminal_status_async(
                operation_name="async poll reused coroutine",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 2

    asyncio.run(run())


def test_retry_operation_async_does_not_retry_reused_coroutines():
    async def run() -> None:
        attempts = {"count": 0}

        async def shared_operation() -> str:
            raise ValueError("transient")

        shared_operation_coroutine = shared_operation()

        async def operation() -> str:
            attempts["count"] += 1
            return await shared_operation_coroutine

        with pytest.raises(
            RuntimeError, match="cannot reuse already awaited coroutine"
        ):
            await retry_operation_async(
                operation_name="async retry reused coroutine",
                operation=operation,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 2

    asyncio.run(run())


def test_retry_operation_does_not_retry_runtime_errors_marked_as_already_awaited():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise RuntimeError("coroutine was already awaited")

    with pytest.raises(RuntimeError, match="coroutine was already awaited"):
        retry_operation(
            operation_name="sync retry already-awaited runtime error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_async_generator_reuse_runtime_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise RuntimeError("anext(): asynchronous generator is already running")

    with pytest.raises(RuntimeError, match="asynchronous generator is already running"):
        retry_operation(
            operation_name="sync retry async-generator-reuse runtime error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_async_does_not_retry_runtime_errors_marked_as_already_awaited():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise RuntimeError("coroutine was already awaited")

        with pytest.raises(RuntimeError, match="coroutine was already awaited"):
            await poll_until_terminal_status_async(
                operation_name="async poll already-awaited runtime error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_async_generator_reuse_runtime_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise RuntimeError("anext(): asynchronous generator is already running")

        with pytest.raises(
            RuntimeError, match="asynchronous generator is already running"
        ):
            await poll_until_terminal_status_async(
                operation_name="async poll async-generator-reuse runtime error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_retry_operation_does_not_retry_runtime_errors_for_loop_mismatch():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise RuntimeError("Task got Future attached to a different loop")

    with pytest.raises(RuntimeError, match="different loop"):
        retry_operation(
            operation_name="sync retry loop-mismatch runtime error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_runtime_errors_for_event_loop_binding():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise RuntimeError("Task is bound to a different event loop")

    with pytest.raises(RuntimeError, match="different event loop"):
        retry_operation(
            operation_name="sync retry loop-binding runtime error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_runtime_errors_for_non_thread_safe_loop_operation():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise RuntimeError(
            "Non-thread-safe operation invoked on an event loop other than the current one"
        )

    with pytest.raises(RuntimeError, match="event loop other than the current one"):
        retry_operation(
            operation_name="sync retry non-thread-safe loop runtime error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_retry_operation_does_not_retry_executor_shutdown_runtime_errors():
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise RuntimeError("cannot schedule new futures after interpreter shutdown")

    with pytest.raises(
        RuntimeError, match="cannot schedule new futures after interpreter shutdown"
    ):
        retry_operation(
            operation_name="sync retry executor-shutdown runtime error",
            operation=operation,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_poll_until_terminal_status_async_does_not_retry_runtime_errors_for_closed_loop():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise RuntimeError("Event loop is closed")

        with pytest.raises(RuntimeError, match="Event loop is closed"):
            await poll_until_terminal_status_async(
                operation_name="async poll closed-loop runtime error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_executor_shutdown_runtime_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise RuntimeError("cannot schedule new futures after shutdown")

        with pytest.raises(
            RuntimeError, match="cannot schedule new futures after shutdown"
        ):
            await poll_until_terminal_status_async(
                operation_name="async poll executor-shutdown runtime error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_runtime_errors_for_non_thread_safe_loop_operation():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise RuntimeError(
                "Non-thread-safe operation invoked on an event loop other than the current one"
            )

        with pytest.raises(RuntimeError, match="event loop other than the current one"):
            await poll_until_terminal_status_async(
                operation_name="async poll non-thread-safe loop runtime error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_poll_until_terminal_status_async_does_not_retry_runtime_errors_for_event_loop_binding():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_status() -> str:
            attempts["count"] += 1
            raise RuntimeError("Task is bound to a different event loop")

        with pytest.raises(RuntimeError, match="different event loop"):
            await poll_until_terminal_status_async(
                operation_name="async poll loop-binding runtime error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
            )

        assert attempts["count"] == 1

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

    attempts = {"count": 0}

    def get_next_page(page: int) -> object:
        attempts["count"] += 1
        return async_get_page()

    with pytest.raises(
        HyperbrowserError, match="get_next_page must return a non-awaitable result"
    ):
        collect_paginated_results(
            operation_name="sync paginated awaitable page callback",
            get_next_page=get_next_page,  # type: ignore[arg-type]
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_cancels_future_page_callback_results():
    loop = asyncio.new_event_loop()
    try:
        page_future = loop.create_future()

        with pytest.raises(
            HyperbrowserError, match="get_next_page must return a non-awaitable result"
        ):
            collect_paginated_results(
                operation_name="sync paginated page future",
                get_next_page=lambda page: page_future,  # type: ignore[return-value]
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert page_future.cancelled()
    finally:
        loop.close()


def test_collect_paginated_results_rejects_awaitable_on_page_success_result():
    callback_attempts = {"count": 0}

    def on_page_success(response: dict) -> object:
        callback_attempts["count"] += 1
        return asyncio.sleep(0)

    with pytest.raises(
        HyperbrowserError, match="on_page_success must return a non-awaitable result"
    ):
        collect_paginated_results(
            operation_name="sync paginated awaitable success callback",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=on_page_success,  # type: ignore[arg-type]
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert callback_attempts["count"] == 1


def test_collect_paginated_results_cancels_future_on_page_success_results():
    loop = asyncio.new_event_loop()
    try:
        callback_future = loop.create_future()

        with pytest.raises(
            HyperbrowserError,
            match="on_page_success must return a non-awaitable result",
        ):
            collect_paginated_results(
                operation_name="sync paginated on-page-success future",
                get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: callback_future,  # type: ignore[return-value]
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert callback_future.cancelled()
    finally:
        loop.close()


def test_collect_paginated_results_fails_fast_when_on_page_success_raises():
    page_attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        page_attempts["count"] += 1
        return {"current": 1, "total": 1, "items": []}

    with pytest.raises(HyperbrowserError, match="on_page_success failed"):
        collect_paginated_results(
            operation_name="sync paginated callback exception",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: (_ for _ in ()).throw(ValueError("boom")),
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert page_attempts["count"] == 1


def test_collect_paginated_results_fails_fast_when_page_batch_callback_raises():
    page_attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        page_attempts["count"] += 1
        return {"current": 1, "total": 1, "items": []}

    with pytest.raises(HyperbrowserError, match="get_current_page_batch failed"):
        collect_paginated_results(
            operation_name="sync paginated page-batch callback exception",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["missing"],  # type: ignore[index]
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert page_attempts["count"] == 1


def test_collect_paginated_results_rejects_awaitable_current_page_callback_result():
    with pytest.raises(
        HyperbrowserError,
        match="get_current_page_batch must return a non-awaitable result",
    ):
        collect_paginated_results(
            operation_name="sync paginated awaitable current page callback",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: asyncio.sleep(0),  # type: ignore[return-value]
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )


def test_collect_paginated_results_rejects_awaitable_total_pages_callback_result():
    with pytest.raises(
        HyperbrowserError,
        match="get_total_page_batches must return a non-awaitable result",
    ):
        collect_paginated_results(
            operation_name="sync paginated awaitable total pages callback",
            get_next_page=lambda page: {"current": 1, "total": 1, "items": []},
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: asyncio.sleep(0),  # type: ignore[return-value]
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
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
        attempts = {"count": 0}

        def get_next_page(page: int) -> object:
            attempts["count"] += 1
            return {"current": 1, "total": 1, "items": []}

        with pytest.raises(
            HyperbrowserError, match="get_next_page must return an awaitable"
        ):
            await collect_paginated_results_async(
                operation_name="async paginated awaitable validation",
                get_next_page=get_next_page,  # type: ignore[arg-type]
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )
        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_rejects_awaitable_on_page_success_result():
    async def run() -> None:
        callback_attempts = {"count": 0}

        def on_page_success(response: dict) -> object:
            callback_attempts["count"] += 1
            return asyncio.sleep(0)

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
                on_page_success=on_page_success,  # type: ignore[arg-type]
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )
        assert callback_attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_cancels_future_on_page_success_results():
    async def run() -> None:
        callback_future = asyncio.get_running_loop().create_future()

        with pytest.raises(
            HyperbrowserError,
            match="on_page_success must return a non-awaitable result",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated on-page-success future",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": 1, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: callback_future,  # type: ignore[return-value]
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert callback_future.cancelled()

    asyncio.run(run())


def test_collect_paginated_results_async_fails_fast_when_on_page_success_raises():
    async def run() -> None:
        page_attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            page_attempts["count"] += 1
            return {"current": 1, "total": 1, "items": []}

        with pytest.raises(HyperbrowserError, match="on_page_success failed"):
            await collect_paginated_results_async(
                operation_name="async paginated callback exception",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: (_ for _ in ()).throw(
                    ValueError("boom")
                ),
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert page_attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_fails_fast_when_page_batch_callback_raises():
    async def run() -> None:
        page_attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            page_attempts["count"] += 1
            return {"current": 1, "total": 1, "items": []}

        with pytest.raises(HyperbrowserError, match="get_total_page_batches failed"):
            await collect_paginated_results_async(
                operation_name="async paginated page-batch callback exception",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["missing"],  # type: ignore[index]
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert page_attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_rejects_awaitable_current_page_callback_result():
    async def run() -> None:
        callback_future = asyncio.get_running_loop().create_future()

        with pytest.raises(
            HyperbrowserError,
            match="get_current_page_batch must return a non-awaitable result",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated awaitable current page callback",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": 1, "items": []}
                ),
                get_current_page_batch=lambda response: callback_future,  # type: ignore[return-value]
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )
        assert callback_future.cancelled()

    asyncio.run(run())


def test_collect_paginated_results_async_rejects_awaitable_total_pages_callback_result():
    async def run() -> None:
        with pytest.raises(
            HyperbrowserError,
            match="get_total_page_batches must return a non-awaitable result",
        ):
            await collect_paginated_results_async(
                operation_name="async paginated awaitable total pages callback",
                get_next_page=lambda page: asyncio.sleep(
                    0, result={"current": 1, "total": 1, "items": []}
                ),
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: asyncio.sleep(0),  # type: ignore[return-value]
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
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


def test_collect_paginated_results_does_not_retry_non_retryable_client_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise HyperbrowserError("client failure", status_code=400)

    with pytest.raises(HyperbrowserError, match="client failure"):
        collect_paginated_results(
            operation_name="sync paginated client error",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_stop_iteration_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise StopIteration("callback exhausted")

    with pytest.raises(StopIteration, match="callback exhausted"):
        collect_paginated_results(
            operation_name="sync paginated stop-iteration passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_generator_reentrancy_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise ValueError("generator already executing")

    with pytest.raises(ValueError, match="generator already executing"):
        collect_paginated_results(
            operation_name="sync paginated generator-reentrancy passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_timeout_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise HyperbrowserTimeoutError("timed out internally")

    with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
        collect_paginated_results(
            operation_name="sync paginated timeout passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_concurrent_cancelled_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise ConcurrentCancelledError()

    with pytest.raises(ConcurrentCancelledError):
        collect_paginated_results(
            operation_name="sync paginated concurrent-cancelled passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_broken_executor_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise ConcurrentBrokenExecutor("executor is broken")

    with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
        collect_paginated_results(
            operation_name="sync paginated broken-executor passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_invalid_state_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise asyncio.InvalidStateError("invalid async state")

    with pytest.raises(asyncio.InvalidStateError, match="invalid async state"):
        collect_paginated_results(
            operation_name="sync paginated invalid-state passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_does_not_retry_executor_shutdown_runtime_errors():
    attempts = {"count": 0}

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        raise RuntimeError("cannot schedule new futures after shutdown")

    with pytest.raises(
        RuntimeError, match="cannot schedule new futures after shutdown"
    ):
        collect_paginated_results(
            operation_name="sync paginated executor-shutdown passthrough",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: None,
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

    assert attempts["count"] == 1


def test_collect_paginated_results_retries_server_errors():
    attempts = {"count": 0}
    collected = []

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("server failure", status_code=502)
        return {"current": 1, "total": 1, "items": ["a"]}

    collect_paginated_results(
        operation_name="sync paginated server error retries",
        get_next_page=get_next_page,
        get_current_page_batch=lambda response: response["current"],
        get_total_page_batches=lambda response: response["total"],
        on_page_success=lambda response: collected.extend(response["items"]),
        max_wait_seconds=1.0,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert collected == ["a"]
    assert attempts["count"] == 3


def test_collect_paginated_results_retries_rate_limit_errors():
    attempts = {"count": 0}
    collected = []

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("rate limited", status_code=429)
        return {"current": 1, "total": 1, "items": ["a"]}

    collect_paginated_results(
        operation_name="sync paginated rate limit retries",
        get_next_page=get_next_page,
        get_current_page_batch=lambda response: response["current"],
        get_total_page_batches=lambda response: response["total"],
        on_page_success=lambda response: collected.extend(response["items"]),
        max_wait_seconds=1.0,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert collected == ["a"]
    assert attempts["count"] == 3


def test_collect_paginated_results_retries_request_timeout_errors():
    attempts = {"count": 0}
    collected = []

    def get_next_page(page: int) -> dict:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HyperbrowserError("request timeout", status_code=408)
        return {"current": 1, "total": 1, "items": ["a"]}

    collect_paginated_results(
        operation_name="sync paginated request-timeout retries",
        get_next_page=get_next_page,
        get_current_page_batch=lambda response: response["current"],
        get_total_page_batches=lambda response: response["total"],
        on_page_success=lambda response: collected.extend(response["items"]),
        max_wait_seconds=1.0,
        max_attempts=5,
        retry_delay_seconds=0.0001,
    )

    assert collected == ["a"]
    assert attempts["count"] == 3


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


def test_collect_paginated_results_async_does_not_retry_non_retryable_client_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise HyperbrowserError("client failure", status_code=404)

        with pytest.raises(HyperbrowserError, match="client failure"):
            await collect_paginated_results_async(
                operation_name="async paginated client error",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_stop_async_iteration_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise StopAsyncIteration("callback exhausted")

        with pytest.raises(StopAsyncIteration, match="callback exhausted"):
            await collect_paginated_results_async(
                operation_name="async paginated stop-async-iteration passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_generator_reentrancy_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise ValueError("generator already executing")

        with pytest.raises(ValueError, match="generator already executing"):
            await collect_paginated_results_async(
                operation_name="async paginated generator-reentrancy passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_timeout_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise HyperbrowserTimeoutError("timed out internally")

        with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
            await collect_paginated_results_async(
                operation_name="async paginated timeout passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_concurrent_cancelled_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise ConcurrentCancelledError()

        with pytest.raises(ConcurrentCancelledError):
            await collect_paginated_results_async(
                operation_name="async paginated concurrent-cancelled passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_broken_executor_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise ConcurrentBrokenExecutor("executor is broken")

        with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
            await collect_paginated_results_async(
                operation_name="async paginated broken-executor passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_invalid_state_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise ConcurrentInvalidStateError("invalid executor state")

        with pytest.raises(ConcurrentInvalidStateError, match="invalid executor state"):
            await collect_paginated_results_async(
                operation_name="async paginated invalid-state passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_executor_shutdown_runtime_errors():
    async def run() -> None:
        attempts = {"count": 0}

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            raise RuntimeError("cannot schedule new futures after shutdown")

        with pytest.raises(
            RuntimeError, match="cannot schedule new futures after shutdown"
        ):
            await collect_paginated_results_async(
                operation_name="async paginated executor-shutdown passthrough",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 1

    asyncio.run(run())


def test_collect_paginated_results_async_retries_server_errors():
    async def run() -> None:
        attempts = {"count": 0}
        collected = []

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("server failure", status_code=503)
            return {"current": 1, "total": 1, "items": ["a"]}

        await collect_paginated_results_async(
            operation_name="async paginated server error retries",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: collected.extend(response["items"]),
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert collected == ["a"]
        assert attempts["count"] == 3

    asyncio.run(run())


def test_collect_paginated_results_async_retries_rate_limit_errors():
    async def run() -> None:
        attempts = {"count": 0}
        collected = []

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("rate limited", status_code=429)
            return {"current": 1, "total": 1, "items": ["a"]}

        await collect_paginated_results_async(
            operation_name="async paginated rate limit retries",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: collected.extend(response["items"]),
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert collected == ["a"]
        assert attempts["count"] == 3

    asyncio.run(run())


def test_collect_paginated_results_async_retries_request_timeout_errors():
    async def run() -> None:
        attempts = {"count": 0}
        collected = []

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise HyperbrowserError("request timeout", status_code=408)
            return {"current": 1, "total": 1, "items": ["a"]}

        await collect_paginated_results_async(
            operation_name="async paginated request-timeout retries",
            get_next_page=get_next_page,
            get_current_page_batch=lambda response: response["current"],
            get_total_page_batches=lambda response: response["total"],
            on_page_success=lambda response: collected.extend(response["items"]),
            max_wait_seconds=1.0,
            max_attempts=5,
            retry_delay_seconds=0.0001,
        )

        assert collected == ["a"]
        assert attempts["count"] == 3

    asyncio.run(run())


def test_collect_paginated_results_async_does_not_retry_reused_coroutines():
    async def run() -> None:
        attempts = {"count": 0}
        shared_page_coroutine = asyncio.sleep(
            0, result={"current": 1, "total": 2, "items": []}
        )

        async def get_next_page(page: int) -> dict:
            attempts["count"] += 1
            return await shared_page_coroutine

        with pytest.raises(
            RuntimeError, match="cannot reuse already awaited coroutine"
        ):
            await collect_paginated_results_async(
                operation_name="async paginated reused coroutine",
                get_next_page=get_next_page,
                get_current_page_batch=lambda response: response["current"],
                get_total_page_batches=lambda response: response["total"],
                on_page_success=lambda response: None,
                max_wait_seconds=1.0,
                max_attempts=5,
                retry_delay_seconds=0.0001,
            )

        assert attempts["count"] == 2

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


def test_wait_for_job_result_status_polling_failures_short_circuit_fetch():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise ValueError("temporary failure")

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserPollingError, match="Failed to poll"):
        wait_for_job_result(
            operation_name="sync wait helper polling failures",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=2,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 2
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_status_timeout_short_circuits_fetch():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        return "running"

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserTimeoutError, match="Timed out waiting for"):
        wait_for_job_result(
            operation_name="sync wait helper status timeout",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_non_retryable_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise HyperbrowserError("client failure", status_code=400)

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserError, match="client failure"):
        wait_for_job_result(
            operation_name="sync wait helper status client error",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_numeric_string_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise HyperbrowserError(
            "client failure",
            status_code="400",  # type: ignore[arg-type]
        )

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserError, match="client failure"):
        wait_for_job_result(
            operation_name="sync wait helper status numeric-string client error",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_numeric_bytes_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise HyperbrowserError(
            "client failure",
            status_code=b"400",  # type: ignore[arg-type]
        )

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserError, match="client failure"):
        wait_for_job_result(
            operation_name="sync wait helper status numeric-bytes client error",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_broken_executor_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise ConcurrentBrokenExecutor("executor is broken")

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
        wait_for_job_result(
            operation_name="sync wait helper status broken-executor",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_invalid_state_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise asyncio.InvalidStateError("invalid async state")

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(asyncio.InvalidStateError, match="invalid async state"):
        wait_for_job_result(
            operation_name="sync wait helper status invalid-state",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_executor_shutdown_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise RuntimeError("cannot schedule new futures after shutdown")

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(
        RuntimeError, match="cannot schedule new futures after shutdown"
    ):
        wait_for_job_result(
            operation_name="sync wait helper status executor-shutdown",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_timeout_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise HyperbrowserTimeoutError("timed out internally")

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
        wait_for_job_result(
            operation_name="sync wait helper status timeout",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_stop_iteration_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise StopIteration("callback exhausted")

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(StopIteration, match="callback exhausted"):
        wait_for_job_result(
            operation_name="sync wait helper status stop-iteration",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_concurrent_cancelled_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        raise ConcurrentCancelledError()

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(ConcurrentCancelledError):
        wait_for_job_result(
            operation_name="sync wait helper status concurrent-cancelled",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_does_not_retry_terminal_callback_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        return "completed"

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    with pytest.raises(HyperbrowserError, match="is_terminal_status failed"):
        wait_for_job_result(
            operation_name="sync wait helper terminal callback exception",
            get_status=get_status,
            is_terminal_status=lambda value: (_ for _ in ()).throw(ValueError("boom")),
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_cancels_awaitable_terminal_callback_results():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}
    loop = asyncio.new_event_loop()
    try:
        callback_future = loop.create_future()

        def get_status() -> str:
            status_attempts["count"] += 1
            return "completed"

        def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(
            HyperbrowserError,
            match="is_terminal_status must return a non-awaitable result",
        ):
            wait_for_job_result(
                operation_name="sync wait helper terminal callback future",
                get_status=get_status,
                is_terminal_status=lambda value: callback_future,  # type: ignore[return-value]
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert callback_future.cancelled()
    finally:
        loop.close()

    assert status_attempts["count"] == 1
    assert fetch_attempts["count"] == 0


def test_wait_for_job_result_retries_rate_limit_status_errors():
    status_attempts = {"count": 0}
    fetch_attempts = {"count": 0}

    def get_status() -> str:
        status_attempts["count"] += 1
        if status_attempts["count"] < 3:
            raise HyperbrowserError("rate limited", status_code=429)
        return "completed"

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        return {"ok": True}

    result = wait_for_job_result(
        operation_name="sync wait helper status rate-limit retries",
        get_status=get_status,
        is_terminal_status=lambda value: value == "completed",
        fetch_result=fetch_result,
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
        fetch_max_attempts=5,
        fetch_retry_delay_seconds=0.0001,
    )

    assert result == {"ok": True}
    assert status_attempts["count"] == 3
    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_non_retryable_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise HyperbrowserError("client failure", status_code=400)

    with pytest.raises(HyperbrowserError, match="client failure"):
        wait_for_job_result(
            operation_name="sync wait helper client error",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=2,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_broken_executor_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise ConcurrentBrokenExecutor("executor is broken")

    with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
        wait_for_job_result(
            operation_name="sync wait helper fetch broken-executor",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_invalid_state_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise ConcurrentInvalidStateError("invalid executor state")

    with pytest.raises(ConcurrentInvalidStateError, match="invalid executor state"):
        wait_for_job_result(
            operation_name="sync wait helper fetch invalid-state",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_executor_shutdown_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise RuntimeError("cannot schedule new futures after shutdown")

    with pytest.raises(
        RuntimeError, match="cannot schedule new futures after shutdown"
    ):
        wait_for_job_result(
            operation_name="sync wait helper fetch executor-shutdown",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_timeout_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise HyperbrowserTimeoutError("timed out internally")

    with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
        wait_for_job_result(
            operation_name="sync wait helper fetch timeout",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_stop_iteration_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise StopIteration("callback exhausted")

    with pytest.raises(StopIteration, match="callback exhausted"):
        wait_for_job_result(
            operation_name="sync wait helper fetch stop-iteration",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_does_not_retry_concurrent_cancelled_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise ConcurrentCancelledError()

    with pytest.raises(ConcurrentCancelledError):
        wait_for_job_result(
            operation_name="sync wait helper fetch concurrent-cancelled",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_cancels_awaitable_fetch_results():
    loop = asyncio.new_event_loop()
    try:
        fetch_attempts = {"count": 0}
        fetch_future = loop.create_future()

        def fetch_result() -> object:
            fetch_attempts["count"] += 1
            return fetch_future

        with pytest.raises(
            HyperbrowserError, match="operation must return a non-awaitable result"
        ):
            wait_for_job_result(
                operation_name="sync wait helper fetch future",
                get_status=lambda: "completed",
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,  # type: ignore[arg-type]
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1
        assert fetch_future.cancelled()
    finally:
        loop.close()


def test_wait_for_job_result_does_not_retry_loop_runtime_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        raise RuntimeError("Task is bound to a different event loop")

    with pytest.raises(RuntimeError, match="different event loop"):
        wait_for_job_result(
            operation_name="sync wait helper fetch loop-runtime",
            get_status=lambda: "completed",
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

    assert fetch_attempts["count"] == 1


def test_wait_for_job_result_retries_rate_limit_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        if fetch_attempts["count"] < 3:
            raise HyperbrowserError("rate limited", status_code=429)
        return {"ok": True}

    result = wait_for_job_result(
        operation_name="sync wait helper rate limit retries",
        get_status=lambda: "completed",
        is_terminal_status=lambda value: value == "completed",
        fetch_result=fetch_result,
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=2,
        fetch_max_attempts=5,
        fetch_retry_delay_seconds=0.0001,
    )

    assert result == {"ok": True}
    assert fetch_attempts["count"] == 3


def test_wait_for_job_result_retries_numeric_string_rate_limit_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        if fetch_attempts["count"] < 3:
            raise HyperbrowserError(
                "rate limited",
                status_code="429",  # type: ignore[arg-type]
            )
        return {"ok": True}

    result = wait_for_job_result(
        operation_name="sync wait helper fetch numeric-string rate limit",
        get_status=lambda: "completed",
        is_terminal_status=lambda value: value == "completed",
        fetch_result=fetch_result,
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
        fetch_max_attempts=5,
        fetch_retry_delay_seconds=0.0001,
    )

    assert result == {"ok": True}
    assert fetch_attempts["count"] == 3


def test_wait_for_job_result_retries_numeric_bytes_rate_limit_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        if fetch_attempts["count"] < 3:
            raise HyperbrowserError(
                "rate limited",
                status_code=b"429",  # type: ignore[arg-type]
            )
        return {"ok": True}

    result = wait_for_job_result(
        operation_name="sync wait helper fetch numeric-bytes rate limit",
        get_status=lambda: "completed",
        is_terminal_status=lambda value: value == "completed",
        fetch_result=fetch_result,
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=5,
        fetch_max_attempts=5,
        fetch_retry_delay_seconds=0.0001,
    )

    assert result == {"ok": True}
    assert fetch_attempts["count"] == 3


def test_wait_for_job_result_retries_request_timeout_fetch_errors():
    fetch_attempts = {"count": 0}

    def fetch_result() -> dict:
        fetch_attempts["count"] += 1
        if fetch_attempts["count"] < 3:
            raise HyperbrowserError("request timeout", status_code=408)
        return {"ok": True}

    result = wait_for_job_result(
        operation_name="sync wait helper request-timeout retries",
        get_status=lambda: "completed",
        is_terminal_status=lambda value: value == "completed",
        fetch_result=fetch_result,
        poll_interval_seconds=0.0001,
        max_wait_seconds=1.0,
        max_status_failures=2,
        fetch_max_attempts=5,
        fetch_retry_delay_seconds=0.0001,
    )

    assert result == {"ok": True}
    assert fetch_attempts["count"] == 3


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


def test_wait_for_job_result_async_status_polling_failures_short_circuit_fetch():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise ValueError("temporary failure")

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserPollingError, match="Failed to poll"):
            await wait_for_job_result_async(
                operation_name="async wait helper polling failures",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=2,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 2
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_status_timeout_short_circuits_fetch():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            return "running"

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserTimeoutError, match="Timed out waiting for"):
            await wait_for_job_result_async(
                operation_name="async wait helper status timeout",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_non_retryable_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise HyperbrowserError("client failure", status_code=404)

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserError, match="client failure"):
            await wait_for_job_result_async(
                operation_name="async wait helper status client error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_numeric_string_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise HyperbrowserError(
                "client failure",
                status_code="404",  # type: ignore[arg-type]
            )

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserError, match="client failure"):
            await wait_for_job_result_async(
                operation_name="async wait helper status numeric-string client error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_numeric_bytes_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise HyperbrowserError(
                "client failure",
                status_code=b"404",  # type: ignore[arg-type]
            )

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserError, match="client failure"):
            await wait_for_job_result_async(
                operation_name="async wait helper status numeric-bytes client error",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_broken_executor_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise ConcurrentBrokenExecutor("executor is broken")

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
            await wait_for_job_result_async(
                operation_name="async wait helper status broken-executor",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_invalid_state_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise ConcurrentInvalidStateError("invalid executor state")

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(ConcurrentInvalidStateError, match="invalid executor state"):
            await wait_for_job_result_async(
                operation_name="async wait helper status invalid-state",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_executor_shutdown_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise RuntimeError("cannot schedule new futures after shutdown")

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(
            RuntimeError, match="cannot schedule new futures after shutdown"
        ):
            await wait_for_job_result_async(
                operation_name="async wait helper status executor-shutdown",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_timeout_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise HyperbrowserTimeoutError("timed out internally")

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
            await wait_for_job_result_async(
                operation_name="async wait helper status timeout",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_stop_async_iteration_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise StopAsyncIteration("callback exhausted")

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(StopAsyncIteration, match="callback exhausted"):
            await wait_for_job_result_async(
                operation_name="async wait helper status stop-async-iteration",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_concurrent_cancelled_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            raise ConcurrentCancelledError()

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(ConcurrentCancelledError):
            await wait_for_job_result_async(
                operation_name="async wait helper status concurrent-cancelled",
                get_status=get_status,
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_terminal_callback_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            return "completed"

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(HyperbrowserError, match="is_terminal_status failed"):
            await wait_for_job_result_async(
                operation_name="async wait helper terminal callback exception",
                get_status=get_status,
                is_terminal_status=lambda value: (_ for _ in ()).throw(
                    ValueError("boom")
                ),
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_cancels_awaitable_terminal_callback_results():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}
        callback_future = asyncio.get_running_loop().create_future()

        async def get_status() -> str:
            status_attempts["count"] += 1
            return "completed"

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(
            HyperbrowserError,
            match="is_terminal_status must return a non-awaitable result",
        ):
            await wait_for_job_result_async(
                operation_name="async wait helper terminal callback future",
                get_status=get_status,
                is_terminal_status=lambda value: callback_future,  # type: ignore[return-value]
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert callback_future.cancelled()
        assert status_attempts["count"] == 1
        assert fetch_attempts["count"] == 0

    asyncio.run(run())


def test_wait_for_job_result_async_retries_rate_limit_status_errors():
    async def run() -> None:
        status_attempts = {"count": 0}
        fetch_attempts = {"count": 0}

        async def get_status() -> str:
            status_attempts["count"] += 1
            if status_attempts["count"] < 3:
                raise HyperbrowserError("rate limited", status_code=429)
            return "completed"

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            return {"ok": True}

        result = await wait_for_job_result_async(
            operation_name="async wait helper status rate-limit retries",
            get_status=get_status,
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

        assert result == {"ok": True}
        assert status_attempts["count"] == 3
        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_non_retryable_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise HyperbrowserError("client failure", status_code=404)

        with pytest.raises(HyperbrowserError, match="client failure"):
            await wait_for_job_result_async(
                operation_name="async wait helper client error",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=2,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_broken_executor_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise ConcurrentBrokenExecutor("executor is broken")

        with pytest.raises(ConcurrentBrokenExecutor, match="executor is broken"):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch broken-executor",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_invalid_state_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise asyncio.InvalidStateError("invalid async state")

        with pytest.raises(asyncio.InvalidStateError, match="invalid async state"):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch invalid-state",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_executor_shutdown_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise RuntimeError("cannot schedule new futures after shutdown")

        with pytest.raises(
            RuntimeError, match="cannot schedule new futures after shutdown"
        ):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch executor-shutdown",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_timeout_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise HyperbrowserTimeoutError("timed out internally")

        with pytest.raises(HyperbrowserTimeoutError, match="timed out internally"):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch timeout",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_stop_async_iteration_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise StopAsyncIteration("callback exhausted")

        with pytest.raises(StopAsyncIteration, match="callback exhausted"):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch stop-async-iteration",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_concurrent_cancelled_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise ConcurrentCancelledError()

        with pytest.raises(ConcurrentCancelledError):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch concurrent-cancelled",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_rejects_non_awaitable_fetch_results():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        def fetch_result() -> object:
            fetch_attempts["count"] += 1
            return {"ok": True}

        with pytest.raises(
            HyperbrowserError, match="operation must return an awaitable"
        ):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch non-awaitable",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,  # type: ignore[arg-type]
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_does_not_retry_loop_runtime_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            raise RuntimeError("Event loop is closed")

        with pytest.raises(RuntimeError, match="Event loop is closed"):
            await wait_for_job_result_async(
                operation_name="async wait helper fetch loop-runtime",
                get_status=lambda: asyncio.sleep(0, result="completed"),
                is_terminal_status=lambda value: value == "completed",
                fetch_result=fetch_result,
                poll_interval_seconds=0.0001,
                max_wait_seconds=1.0,
                max_status_failures=5,
                fetch_max_attempts=5,
                fetch_retry_delay_seconds=0.0001,
            )

        assert fetch_attempts["count"] == 1

    asyncio.run(run())


def test_wait_for_job_result_async_retries_rate_limit_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            if fetch_attempts["count"] < 3:
                raise HyperbrowserError("rate limited", status_code=429)
            return {"ok": True}

        result = await wait_for_job_result_async(
            operation_name="async wait helper rate limit retries",
            get_status=lambda: asyncio.sleep(0, result="completed"),
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=2,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

        assert result == {"ok": True}
        assert fetch_attempts["count"] == 3

    asyncio.run(run())


def test_wait_for_job_result_async_retries_numeric_string_rate_limit_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            if fetch_attempts["count"] < 3:
                raise HyperbrowserError(
                    "rate limited",
                    status_code=" 429 ",  # type: ignore[arg-type]
                )
            return {"ok": True}

        result = await wait_for_job_result_async(
            operation_name="async wait helper fetch numeric-string rate limit",
            get_status=lambda: asyncio.sleep(0, result="completed"),
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

        assert result == {"ok": True}
        assert fetch_attempts["count"] == 3

    asyncio.run(run())


def test_wait_for_job_result_async_retries_numeric_bytes_rate_limit_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            if fetch_attempts["count"] < 3:
                raise HyperbrowserError(
                    "rate limited",
                    status_code=b"429",  # type: ignore[arg-type]
                )
            return {"ok": True}

        result = await wait_for_job_result_async(
            operation_name="async wait helper fetch numeric-bytes rate limit",
            get_status=lambda: asyncio.sleep(0, result="completed"),
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=5,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

        assert result == {"ok": True}
        assert fetch_attempts["count"] == 3

    asyncio.run(run())


def test_wait_for_job_result_async_retries_request_timeout_fetch_errors():
    async def run() -> None:
        fetch_attempts = {"count": 0}

        async def fetch_result() -> dict:
            fetch_attempts["count"] += 1
            if fetch_attempts["count"] < 3:
                raise HyperbrowserError("request timeout", status_code=408)
            return {"ok": True}

        result = await wait_for_job_result_async(
            operation_name="async wait helper request-timeout retries",
            get_status=lambda: asyncio.sleep(0, result="completed"),
            is_terminal_status=lambda value: value == "completed",
            fetch_result=fetch_result,
            poll_interval_seconds=0.0001,
            max_wait_seconds=1.0,
            max_status_failures=2,
            fetch_max_attempts=5,
            fetch_retry_delay_seconds=0.0001,
        )

        assert result == {"ok": True}
        assert fetch_attempts["count"] == 3

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
