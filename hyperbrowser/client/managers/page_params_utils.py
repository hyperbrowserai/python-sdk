from typing import Type, TypeVar, cast

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.type_utils import is_plain_int

DEFAULT_PAGE_BATCH_SIZE = 100

T = TypeVar("T")


def build_page_batch_params(
    params_model: Type[T],
    *,
    page: int,
    batch_size: int = DEFAULT_PAGE_BATCH_SIZE,
) -> T:
    if not is_plain_int(page):
        raise HyperbrowserError("page must be a plain integer")
    if page <= 0:
        raise HyperbrowserError("page must be a positive integer")
    if not is_plain_int(batch_size):
        raise HyperbrowserError("batch_size must be a plain integer")
    if batch_size <= 0:
        raise HyperbrowserError("batch_size must be a positive integer")
    try:
        return cast(T, params_model(page=page, batch_size=batch_size))
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "Failed to build paginated page params",
            original_error=exc,
        ) from exc
