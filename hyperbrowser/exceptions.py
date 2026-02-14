# exceptions.py
from typing import Optional, Any

from hyperbrowser.type_utils import is_plain_string

_MAX_EXCEPTION_DISPLAY_LENGTH = 2000
_TRUNCATED_EXCEPTION_DISPLAY_SUFFIX = "... (truncated)"


def _truncate_exception_text(text_value: str) -> str:
    if len(text_value) <= _MAX_EXCEPTION_DISPLAY_LENGTH:
        return text_value
    available_length = _MAX_EXCEPTION_DISPLAY_LENGTH - len(
        _TRUNCATED_EXCEPTION_DISPLAY_SUFFIX
    )
    if available_length <= 0:
        return _TRUNCATED_EXCEPTION_DISPLAY_SUFFIX
    return f"{text_value[:available_length]}{_TRUNCATED_EXCEPTION_DISPLAY_SUFFIX}"


def _safe_exception_text(value: Any, *, fallback: str) -> str:
    try:
        text_value = str(value)
    except Exception:
        return fallback
    if not is_plain_string(text_value):
        return fallback
    try:
        sanitized_value = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in text_value
        )
        if not is_plain_string(sanitized_value):
            return fallback
        if sanitized_value.strip():
            return _truncate_exception_text(sanitized_value)
    except Exception:
        return fallback
    return fallback


class HyperbrowserError(Exception):
    """Base exception class for Hyperbrowser SDK errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.original_error = original_error

    def __str__(self) -> str:
        """Custom string representation to show a cleaner error message"""
        message_value = self.args[0] if self.args else "Hyperbrowser error"
        message_text = _safe_exception_text(
            message_value,
            fallback="Hyperbrowser error",
        )
        parts = [message_text]

        if self.status_code is not None:
            status_text = _safe_exception_text(
                self.status_code,
                fallback="<unknown status>",
            )
            parts.append(f"Status: {status_text}")

        if self.original_error and not isinstance(
            self.original_error, HyperbrowserError
        ):
            error_type = type(self.original_error).__name__
            error_msg = _safe_exception_text(
                self.original_error,
                fallback=f"<unstringifiable {error_type}>",
            )
            if error_msg != message_text:
                parts.append(f"Caused by {error_type}: {error_msg}")

        return " - ".join(parts)

    def __repr__(self) -> str:
        return self.__str__()


class HyperbrowserTimeoutError(HyperbrowserError):
    """Raised when a polling or wait operation exceeds configured timeout."""


class HyperbrowserPollingError(HyperbrowserError):
    """Raised when a polling operation repeatedly fails to retrieve status."""
