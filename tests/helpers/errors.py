from typing import Callable, Iterable, Optional

from hyperbrowser.exceptions import HyperbrowserError


def _normalize_messages(
    value: Optional[Iterable[str]], single: Optional[str]
):
    if single is not None:
        return [single]
    if value is None:
        return []
    return list(value)


def expect_hyperbrowser_error(
    label: str,
    action: Callable[[], object],
    *,
    status_code: Optional[int] = None,
    code: Optional[str] = None,
    service: Optional[str] = None,
    retryable: Optional[bool] = None,
    message_includes: Optional[str] = None,
    message_includes_many: Optional[Iterable[str]] = None,
    message_includes_any: Optional[Iterable[str]] = None,
):
    try:
        action()
    except HyperbrowserError as error:
        assert "Unknown error occurred" not in str(error), (
            f"{label}: unexpected generic error message {error!r}"
        )

        if status_code is not None:
            assert error.status_code == status_code, (
                f"{label}: expected status_code={status_code}, "
                f"got {error.status_code}"
            )
        if code is not None:
            assert error.code == code, f"{label}: expected code={code}, got {error.code}"
        if service is not None:
            assert error.service == service, (
                f"{label}: expected service={service}, got {error.service}"
            )
        if retryable is not None:
            assert error.retryable == retryable, (
                f"{label}: expected retryable={retryable}, got {error.retryable}"
            )

        for text in _normalize_messages(message_includes_many, message_includes):
            assert text in str(error), (
                f"{label}: expected error message to include {text!r}, "
                f"got {str(error)!r}"
            )

        if message_includes_any:
            assert any(text in str(error) for text in message_includes_any), (
                f"{label}: expected error message to include one of "
                f"{list(message_includes_any)!r}, got {str(error)!r}"
            )

        return error

    raise AssertionError(f"{label}: expected HyperbrowserError, but call succeeded")


async def expect_hyperbrowser_error_async(
    label: str,
    action,
    *,
    status_code: Optional[int] = None,
    code: Optional[str] = None,
    service: Optional[str] = None,
    retryable: Optional[bool] = None,
    message_includes: Optional[str] = None,
    message_includes_many: Optional[Iterable[str]] = None,
    message_includes_any: Optional[Iterable[str]] = None,
):
    try:
        await action()
    except HyperbrowserError as error:
        assert "Unknown error occurred" not in str(error), (
            f"{label}: unexpected generic error message {error!r}"
        )

        if status_code is not None:
            assert error.status_code == status_code, (
                f"{label}: expected status_code={status_code}, "
                f"got {error.status_code}"
            )
        if code is not None:
            assert error.code == code, f"{label}: expected code={code}, got {error.code}"
        if service is not None:
            assert error.service == service, (
                f"{label}: expected service={service}, got {error.service}"
            )
        if retryable is not None:
            assert error.retryable == retryable, (
                f"{label}: expected retryable={retryable}, got {error.retryable}"
            )

        for text in _normalize_messages(message_includes_many, message_includes):
            assert text in str(error), (
                f"{label}: expected error message to include {text!r}, "
                f"got {str(error)!r}"
            )

        if message_includes_any:
            assert any(text in str(error) for text in message_includes_any), (
                f"{label}: expected error message to include one of "
                f"{list(message_includes_any)!r}, got {str(error)!r}"
            )

        return error

    raise AssertionError(f"{label}: expected HyperbrowserError, but call succeeded")
