# exceptions.py
from typing import Optional, Any


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
        parts = [f"{self.args[0]}"]

        if self.status_code:
            parts.append(f"Status: {self.status_code}")

        if self.original_error and not isinstance(
            self.original_error, HyperbrowserError
        ):
            error_type = type(self.original_error).__name__
            error_msg = str(self.original_error)
            if error_msg and error_msg != str(self.args[0]):
                parts.append(f"Caused by {error_type}: {error_msg}")

        return " - ".join(parts)

    def __repr__(self) -> str:
        return self.__str__()
