import math
from numbers import Real
from typing import Optional

from ..exceptions import HyperbrowserError


def validate_timeout_seconds(timeout: Optional[float]) -> None:
    if timeout is None:
        return
    if isinstance(timeout, bool) or not isinstance(timeout, Real):
        raise HyperbrowserError("timeout must be a number")
    try:
        is_finite = math.isfinite(timeout)
    except (TypeError, ValueError, OverflowError):
        is_finite = False
    if not is_finite:
        raise HyperbrowserError("timeout must be finite")
    if timeout < 0:
        raise HyperbrowserError("timeout must be non-negative")
