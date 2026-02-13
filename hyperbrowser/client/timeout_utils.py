from decimal import Decimal
import math
from numbers import Real
from typing import Optional

from ..exceptions import HyperbrowserError


def validate_timeout_seconds(timeout: Optional[float]) -> Optional[float]:
    if timeout is None:
        return None
    is_supported_numeric_type = isinstance(timeout, Real) or isinstance(
        timeout, Decimal
    )
    if isinstance(timeout, bool) or not is_supported_numeric_type:
        raise HyperbrowserError("timeout must be a number")
    try:
        normalized_timeout = float(timeout)
    except (TypeError, ValueError, OverflowError) as exc:
        raise HyperbrowserError(
            "timeout must be finite",
            original_error=exc,
        ) from exc
    try:
        is_finite = math.isfinite(normalized_timeout)
    except (TypeError, ValueError, OverflowError):
        is_finite = False
    if not is_finite:
        raise HyperbrowserError("timeout must be finite")
    if normalized_timeout < 0:
        raise HyperbrowserError("timeout must be non-negative")
    return normalized_timeout
