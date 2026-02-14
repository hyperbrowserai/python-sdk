import asyncio
from concurrent.futures import BrokenExecutor as ConcurrentBrokenExecutor
from concurrent.futures import CancelledError as ConcurrentCancelledError
from concurrent.futures import InvalidStateError as ConcurrentInvalidStateError
from decimal import Decimal
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
_FETCH_OPERATION_NAME_PREFIX = "Fetching "
_FETCH_PREFIX_KEYWORD = "fetching"
_TRUNCATED_OPERATION_NAME_SUFFIX = "..."
_TRUNCATED_EXCEPTION_TEXT_SUFFIX = "... (truncated)"
_CLIENT_ERROR_STATUS_MIN = 400
_CLIENT_ERROR_STATUS_MAX = 500
_RETRYABLE_CLIENT_ERROR_STATUS_CODES = {408, 429}
_MAX_STATUS_CODE_TEXT_LENGTH = 6
_MAX_EXCEPTION_TEXT_LENGTH = 500


class _NonRetryablePollingError(HyperbrowserError):
    pass


def _safe_exception_text(exc: Exception) -> str:
    try:
        exception_message = str(exc)
    except Exception:
        return f"<unstringifiable {type(exc).__name__}>"
    if type(exception_message) is not str:
        return f"<unstringifiable {type(exc).__name__}>"
    try:
        sanitized_exception_message = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in exception_message
        )
        if type(sanitized_exception_message) is not str:
            return f"<unstringifiable {type(exc).__name__}>"
        if sanitized_exception_message.strip():
            if len(sanitized_exception_message) <= _MAX_EXCEPTION_TEXT_LENGTH:
                return sanitized_exception_message
            available_message_length = _MAX_EXCEPTION_TEXT_LENGTH - len(
                _TRUNCATED_EXCEPTION_TEXT_SUFFIX
            )
            if available_message_length <= 0:
                return _TRUNCATED_EXCEPTION_TEXT_SUFFIX
            return (
                f"{sanitized_exception_message[:available_message_length]}"
                f"{_TRUNCATED_EXCEPTION_TEXT_SUFFIX}"
            )
    except Exception:
        return f"<unstringifiable {type(exc).__name__}>"
    return f"<{type(exc).__name__}>"


def _normalized_exception_text(exc: Exception) -> str:
    return _safe_exception_text(exc).lower()


def _coerce_operation_name_component(value: object, *, fallback: str) -> str:
    if isinstance(value, str) and type(value) is str:
        return value
    try:
        normalized_value = str(value)
        if type(normalized_value) is not str:
            raise TypeError("operation name component must normalize to string")
        return normalized_value
    except Exception:
        return fallback


def _sanitize_operation_name_component(value: str) -> str:
    return "".join(
        "?" if ord(character) < 32 or ord(character) == 127 else character
        for character in value
    )


def _normalize_non_negative_real(value: float, *, field_name: str) -> float:
    is_supported_numeric_type = isinstance(value, Real) or isinstance(value, Decimal)
    if isinstance(value, bool) or not is_supported_numeric_type:
        raise HyperbrowserError(f"{field_name} must be a number")
    try:
        normalized_value = float(value)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"{field_name} must be finite",
            original_error=exc,
        ) from exc
    try:
        is_finite = math.isfinite(normalized_value)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            f"{field_name} must be finite",
            original_error=exc,
        ) from exc
    if not is_finite:
        raise HyperbrowserError(f"{field_name} must be finite")
    if normalized_value < 0:
        raise HyperbrowserError(f"{field_name} must be non-negative")
    return normalized_value


def _validate_operation_name(operation_name: str) -> None:
    if not isinstance(operation_name, str):
        raise HyperbrowserError("operation_name must be a string")
    try:
        normalized_operation_name = operation_name.strip()
        if type(normalized_operation_name) is not str:
            raise TypeError("normalized operation_name must be a string")
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to normalize operation_name",
            original_error=exc,
        ) from exc
    if not normalized_operation_name:
        raise HyperbrowserError("operation_name must not be empty")
    try:
        has_surrounding_whitespace = operation_name != normalized_operation_name
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to normalize operation_name",
            original_error=exc,
        ) from exc
    if has_surrounding_whitespace:
        raise HyperbrowserError(
            "operation_name must not contain leading or trailing whitespace"
        )
    try:
        operation_name_length = len(operation_name)
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to validate operation_name length",
            original_error=exc,
        ) from exc
    if operation_name_length > _MAX_OPERATION_NAME_LENGTH:
        raise HyperbrowserError(
            f"operation_name must be {_MAX_OPERATION_NAME_LENGTH} characters or fewer"
        )
    try:
        contains_control_character = any(
            ord(character) < 32 or ord(character) == 127
            for character in operation_name
        )
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to validate operation_name characters",
            original_error=exc,
        ) from exc
    if contains_control_character:
        raise HyperbrowserError("operation_name must not contain control characters")


def build_operation_name(prefix: object, identifier: object) -> str:
    normalized_prefix = _coerce_operation_name_component(prefix, fallback="")
    normalized_prefix = _sanitize_operation_name_component(normalized_prefix)
    normalized_prefix = normalized_prefix.lstrip()
    has_trailing_whitespace = (
        bool(normalized_prefix) and normalized_prefix[-1].isspace()
    )
    normalized_prefix = normalized_prefix.rstrip()
    if has_trailing_whitespace and normalized_prefix:
        normalized_prefix = f"{normalized_prefix} "
    raw_identifier = _coerce_operation_name_component(identifier, fallback="unknown")
    normalized_identifier = raw_identifier.strip()
    if not normalized_identifier:
        normalized_identifier = "unknown"

    combined_length = len(normalized_prefix) + len(normalized_identifier)
    if combined_length <= _MAX_OPERATION_NAME_LENGTH:
        sanitized_identifier = _sanitize_operation_name_component(normalized_identifier)
        operation_name = f"{normalized_prefix}{sanitized_identifier}".strip()
        if not operation_name:
            return "operation"
        return operation_name
    available_identifier_length = (
        _MAX_OPERATION_NAME_LENGTH
        - len(normalized_prefix)
        - len(_TRUNCATED_OPERATION_NAME_SUFFIX)
    )
    if available_identifier_length > 0:
        truncated_identifier = normalized_identifier[:available_identifier_length]
        sanitized_truncated_identifier = _sanitize_operation_name_component(
            truncated_identifier
        )
        operation_name = (
            f"{normalized_prefix}{sanitized_truncated_identifier}"
            f"{_TRUNCATED_OPERATION_NAME_SUFFIX}"
        )
    else:
        operation_name = normalized_prefix[:_MAX_OPERATION_NAME_LENGTH]
    operation_name = operation_name.strip()
    if not operation_name:
        return "operation"
    return operation_name


def build_fetch_operation_name(operation_name: object) -> str:
    normalized_operation_name = build_operation_name("", operation_name)
    normalized_lower_operation_name = normalized_operation_name.lower()
    if normalized_lower_operation_name.startswith(_FETCH_PREFIX_KEYWORD):
        next_character_index = len(_FETCH_PREFIX_KEYWORD)
        if next_character_index == len(normalized_lower_operation_name):
            return normalized_operation_name
        next_character = normalized_lower_operation_name[next_character_index]
        if not next_character.isalnum():
            return normalized_operation_name
    return build_operation_name(
        _FETCH_OPERATION_NAME_PREFIX,
        normalized_operation_name,
    )


def ensure_started_job_id(job_id: object, *, error_message: str) -> str:
    if not isinstance(job_id, str):
        raise HyperbrowserError(error_message)
    try:
        normalized_job_id = job_id.strip()
        if type(normalized_job_id) is not str:
            raise TypeError("normalized job_id must be a string")
        is_empty_job_id = len(normalized_job_id) == 0
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(error_message, original_error=exc) from exc
    if is_empty_job_id:
        raise HyperbrowserError(error_message)
    return normalized_job_id


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
    if type(status) is not str:
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
        elif isinstance(result, asyncio.Future):
            if result.done():
                try:
                    result.exception()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            else:
                result.cancel()
        raise _NonRetryablePollingError(
            f"{callback_name} must return a non-awaitable result for {operation_name}"
        )


def _invoke_non_retryable_callback(
    callback: Callable[..., T], *args: object, callback_name: str, operation_name: str
) -> T:
    try:
        return callback(*args)
    except _NonRetryablePollingError:
        raise
    except Exception as exc:
        raise _NonRetryablePollingError(
            f"{callback_name} failed for {operation_name}: {_safe_exception_text(exc)}"
        ) from exc


def _is_reused_coroutine_runtime_error(exc: Exception) -> bool:
    if not isinstance(exc, RuntimeError):
        return False
    normalized_message = _normalized_exception_text(exc)
    return "coroutine" in normalized_message and "already awaited" in normalized_message


def _is_async_generator_reuse_runtime_error(exc: Exception) -> bool:
    if not isinstance(exc, RuntimeError):
        return False
    normalized_message = _normalized_exception_text(exc)
    return (
        "asynchronous generator" in normalized_message
        and "already running" in normalized_message
    )


def _is_generator_reentrancy_error(exc: Exception) -> bool:
    if not isinstance(exc, ValueError):
        return False
    return "generator already executing" in _normalized_exception_text(exc)


def _is_async_loop_contract_runtime_error(exc: Exception) -> bool:
    if not isinstance(exc, RuntimeError):
        return False
    normalized_message = _normalized_exception_text(exc)
    if "event loop is closed" in normalized_message:
        return True
    if "event loop other than the current one" in normalized_message:
        return True
    if "attached to a different loop" in normalized_message:
        return True
    if "different event loop" in normalized_message:
        return True
    return "different loop" in normalized_message and any(
        marker in normalized_message for marker in ("future", "task")
    )


def _is_executor_shutdown_runtime_error(exc: Exception) -> bool:
    if not isinstance(exc, RuntimeError):
        return False
    normalized_message = _normalized_exception_text(exc)
    return (
        "cannot schedule new futures after" in normalized_message
        and "shutdown" in normalized_message
    )


def _decode_ascii_bytes_like(value: object) -> Optional[str]:
    try:
        status_buffer = memoryview(value)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    if status_buffer.nbytes > _MAX_STATUS_CODE_TEXT_LENGTH:
        return None
    try:
        return status_buffer.tobytes().decode("ascii")
    except UnicodeDecodeError:
        return None


def _normalize_status_code_for_retry(status_code: object) -> Optional[int]:
    if isinstance(status_code, bool):
        return None
    if isinstance(status_code, int):
        return status_code
    status_text: Optional[str] = None
    if isinstance(status_code, memoryview):
        status_text = _decode_ascii_bytes_like(status_code)
    elif isinstance(status_code, (bytes, bytearray)):
        status_text = _decode_ascii_bytes_like(status_code)
    elif isinstance(status_code, str):
        status_text = status_code
    else:
        status_text = _decode_ascii_bytes_like(status_code)

    if status_text is not None:
        try:
            if type(status_text) is not str:
                return None
            normalized_status = status_text.strip()
            if type(normalized_status) is not str:
                return None
            if not normalized_status:
                return None
            if len(normalized_status) > _MAX_STATUS_CODE_TEXT_LENGTH:
                return None
            if not normalized_status.isascii() or not normalized_status.isdigit():
                return None
        except Exception:
            return None
        try:
            return int(normalized_status, 10)
        except ValueError:
            return None
    return None


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, ConcurrentBrokenExecutor):
        return False
    if isinstance(exc, (asyncio.InvalidStateError, ConcurrentInvalidStateError)):
        return False
    if isinstance(exc, (StopIteration, StopAsyncIteration)):
        return False
    if _is_generator_reentrancy_error(exc):
        return False
    if _is_reused_coroutine_runtime_error(exc):
        return False
    if _is_async_generator_reuse_runtime_error(exc):
        return False
    if _is_async_loop_contract_runtime_error(exc):
        return False
    if _is_executor_shutdown_runtime_error(exc):
        return False
    if isinstance(exc, ConcurrentCancelledError):
        return False
    if isinstance(exc, _NonRetryablePollingError):
        return False
    if isinstance(exc, (HyperbrowserTimeoutError, HyperbrowserPollingError)):
        return False
    if isinstance(exc, HyperbrowserError) and exc.status_code is not None:
        normalized_status_code = _normalize_status_code_for_retry(exc.status_code)
        if normalized_status_code is None:
            return True
        if (
            _CLIENT_ERROR_STATUS_MIN
            <= normalized_status_code
            < _CLIENT_ERROR_STATUS_MAX
            and normalized_status_code not in _RETRYABLE_CLIENT_ERROR_STATUS_CODES
        ):
            return False
    return True


def _validate_retry_config(
    *,
    max_attempts: int,
    retry_delay_seconds: float,
    max_status_failures: Optional[int] = None,
) -> float:
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise HyperbrowserError("max_attempts must be an integer")
    if max_attempts < 1:
        raise HyperbrowserError("max_attempts must be at least 1")
    normalized_retry_delay_seconds = _normalize_non_negative_real(
        retry_delay_seconds, field_name="retry_delay_seconds"
    )
    if max_status_failures is not None:
        if isinstance(max_status_failures, bool) or not isinstance(
            max_status_failures, int
        ):
            raise HyperbrowserError("max_status_failures must be an integer")
        if max_status_failures < 1:
            raise HyperbrowserError("max_status_failures must be at least 1")
    return normalized_retry_delay_seconds


def _validate_poll_interval(poll_interval_seconds: float) -> float:
    return _normalize_non_negative_real(
        poll_interval_seconds,
        field_name="poll_interval_seconds",
    )


def _validate_max_wait_seconds(max_wait_seconds: Optional[float]) -> Optional[float]:
    if max_wait_seconds is None:
        return None
    return _normalize_non_negative_real(max_wait_seconds, field_name="max_wait_seconds")


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
    poll_interval_seconds = _validate_poll_interval(poll_interval_seconds)
    max_wait_seconds = _validate_max_wait_seconds(max_wait_seconds)
    _ = _validate_retry_config(
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
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    "Failed to poll "
                    f"{operation_name} after {max_status_failures} attempts: "
                    f"{_safe_exception_text(exc)}"
                ) from exc
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
                )
            time.sleep(poll_interval_seconds)
            continue

        status = _ensure_status_string(status, operation_name=operation_name)
        terminal_status_result = _invoke_non_retryable_callback(
            is_terminal_status,
            status,
            callback_name="is_terminal_status",
            operation_name=operation_name,
        )
        if _ensure_boolean_terminal_result(
            terminal_status_result, operation_name=operation_name
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
    retry_delay_seconds = _validate_retry_config(
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    failures = 0
    while True:
        try:
            operation_result = operation()
        except Exception as exc:
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: "
                    f"{_safe_exception_text(exc)}"
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
    poll_interval_seconds = _validate_poll_interval(poll_interval_seconds)
    max_wait_seconds = _validate_max_wait_seconds(max_wait_seconds)
    _ = _validate_retry_config(
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
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    "Failed to poll "
                    f"{operation_name} after {max_status_failures} attempts: "
                    f"{_safe_exception_text(exc)}"
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
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_status_failures:
                raise HyperbrowserPollingError(
                    "Failed to poll "
                    f"{operation_name} after {max_status_failures} attempts: "
                    f"{_safe_exception_text(exc)}"
                ) from exc
            if has_exceeded_max_wait(start_time, max_wait_seconds):
                raise HyperbrowserTimeoutError(
                    f"Timed out waiting for {operation_name} after {max_wait_seconds} seconds"
                )
            await asyncio.sleep(poll_interval_seconds)
            continue

        status = _ensure_status_string(status, operation_name=operation_name)
        terminal_status_result = _invoke_non_retryable_callback(
            is_terminal_status,
            status,
            callback_name="is_terminal_status",
            operation_name=operation_name,
        )
        if _ensure_boolean_terminal_result(
            terminal_status_result, operation_name=operation_name
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
    retry_delay_seconds = _validate_retry_config(
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    failures = 0
    while True:
        try:
            operation_result = operation()
        except Exception as exc:
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: "
                    f"{_safe_exception_text(exc)}"
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
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    f"{operation_name} failed after {max_attempts} attempts: "
                    f"{_safe_exception_text(exc)}"
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
    max_wait_seconds = _validate_max_wait_seconds(max_wait_seconds)
    retry_delay_seconds = _validate_retry_config(
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
            callback_result = _invoke_non_retryable_callback(
                on_page_success,
                page_response,
                callback_name="on_page_success",
                operation_name=operation_name,
            )
            _ensure_non_awaitable(
                callback_result,
                callback_name="on_page_success",
                operation_name=operation_name,
            )
            current_page_batch = _invoke_non_retryable_callback(
                get_current_page_batch,
                page_response,
                callback_name="get_current_page_batch",
                operation_name=operation_name,
            )
            _ensure_non_awaitable(
                current_page_batch,
                callback_name="get_current_page_batch",
                operation_name=operation_name,
            )
            total_page_batches = _invoke_non_retryable_callback(
                get_total_page_batches,
                page_response,
                callback_name="get_total_page_batches",
                operation_name=operation_name,
            )
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
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    "Failed to fetch page batch "
                    f"{current_page_batch + 1} for {operation_name} after "
                    f"{max_attempts} attempts: {_safe_exception_text(exc)}"
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
    max_wait_seconds = _validate_max_wait_seconds(max_wait_seconds)
    retry_delay_seconds = _validate_retry_config(
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
            callback_result = _invoke_non_retryable_callback(
                on_page_success,
                page_response,
                callback_name="on_page_success",
                operation_name=operation_name,
            )
            _ensure_non_awaitable(
                callback_result,
                callback_name="on_page_success",
                operation_name=operation_name,
            )
            current_page_batch = _invoke_non_retryable_callback(
                get_current_page_batch,
                page_response,
                callback_name="get_current_page_batch",
                operation_name=operation_name,
            )
            _ensure_non_awaitable(
                current_page_batch,
                callback_name="get_current_page_batch",
                operation_name=operation_name,
            )
            total_page_batches = _invoke_non_retryable_callback(
                get_total_page_batches,
                page_response,
                callback_name="get_total_page_batches",
                operation_name=operation_name,
            )
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
            if not _is_retryable_exception(exc):
                raise
            failures += 1
            if failures >= max_attempts:
                raise HyperbrowserError(
                    "Failed to fetch page batch "
                    f"{current_page_batch + 1} for {operation_name} after "
                    f"{max_attempts} attempts: {_safe_exception_text(exc)}"
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
    fetch_retry_delay_seconds = _validate_retry_config(
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
        max_status_failures=max_status_failures,
    )
    poll_interval_seconds = _validate_poll_interval(poll_interval_seconds)
    max_wait_seconds = _validate_max_wait_seconds(max_wait_seconds)
    poll_until_terminal_status(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
    )
    fetch_operation_name = build_fetch_operation_name(operation_name)
    return retry_operation(
        operation_name=fetch_operation_name,
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
    fetch_retry_delay_seconds = _validate_retry_config(
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
        max_status_failures=max_status_failures,
    )
    poll_interval_seconds = _validate_poll_interval(poll_interval_seconds)
    max_wait_seconds = _validate_max_wait_seconds(max_wait_seconds)
    await poll_until_terminal_status_async(
        operation_name=operation_name,
        get_status=get_status,
        is_terminal_status=is_terminal_status,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        max_status_failures=max_status_failures,
    )
    fetch_operation_name = build_fetch_operation_name(operation_name)
    return await retry_operation_async(
        operation_name=fetch_operation_name,
        operation=fetch_result,
        max_attempts=fetch_max_attempts,
        retry_delay_seconds=fetch_retry_delay_seconds,
    )
