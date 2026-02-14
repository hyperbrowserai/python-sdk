from typing import Any, Callable, Type, TypeVar

T = TypeVar("T")


def initialize_job_paginated_response(
    *,
    model: Type[T],
    job_id: str,
    status: str,
    total_counter_alias: str,
    batch_size: int = 100,
) -> T:
    return model(
        jobId=job_id,
        status=status,
        data=[],
        currentPageBatch=0,
        totalPageBatches=0,
        batchSize=batch_size,
        **{total_counter_alias: 0},
    )


def merge_job_paginated_page_response(
    job_response: Any,
    page_response: Any,
    *,
    total_counter_attr: str,
) -> None:
    if page_response.data:
        job_response.data.extend(page_response.data)
    job_response.current_page_batch = page_response.current_page_batch
    setattr(
        job_response,
        total_counter_attr,
        getattr(page_response, total_counter_attr),
    )
    job_response.total_page_batches = page_response.total_page_batches
    job_response.batch_size = page_response.batch_size
    job_response.error = page_response.error


def build_job_paginated_page_merge_callback(
    *,
    job_response: Any,
    total_counter_attr: str,
) -> Callable[[Any], None]:
    def _merge_callback(page_response: Any) -> None:
        merge_job_paginated_page_response(
            job_response,
            page_response,
            total_counter_attr=total_counter_attr,
        )

    return _merge_callback
