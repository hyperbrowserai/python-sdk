from typing import Any, Callable, Type, TypeVar

from .job_pagination_utils import (
    build_job_paginated_page_merge_callback,
    initialize_job_paginated_response,
    merge_job_paginated_page_response,
)

T = TypeVar("T")

_WEB_TOTAL_COUNTER_ALIAS = "totalPages"
_WEB_TOTAL_COUNTER_ATTR = "total_pages"

def initialize_paginated_job_response(
    *,
    model: Type[T],
    job_id: str,
    status: str,
    batch_size: int = 100,
) -> T:
    return initialize_job_paginated_response(
        model=model,
        job_id=job_id,
        status=status,
        total_counter_alias=_WEB_TOTAL_COUNTER_ALIAS,
        batch_size=batch_size,
    )


def merge_paginated_page_response(job_response: Any, page_response: Any) -> None:
    merge_job_paginated_page_response(
        job_response,
        page_response,
        total_counter_attr=_WEB_TOTAL_COUNTER_ATTR,
    )


def build_paginated_page_merge_callback(*, job_response: Any) -> Callable[[Any], None]:
    return build_job_paginated_page_merge_callback(
        job_response=job_response,
        total_counter_attr=_WEB_TOTAL_COUNTER_ATTR,
    )
