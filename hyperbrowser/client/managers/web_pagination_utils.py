from typing import Any, Type, TypeVar

T = TypeVar("T")


def initialize_paginated_job_response(
    *,
    model: Type[T],
    job_id: str,
    status: str,
    batch_size: int = 100,
) -> T:
    return model(
        jobId=job_id,
        status=status,
        data=[],
        currentPageBatch=0,
        totalPageBatches=0,
        totalPages=0,
        batchSize=batch_size,
    )


def merge_paginated_page_response(job_response: Any, page_response: Any) -> None:
    if page_response.data:
        job_response.data.extend(page_response.data)
    job_response.current_page_batch = page_response.current_page_batch
    job_response.total_pages = page_response.total_pages
    job_response.total_page_batches = page_response.total_page_batches
    job_response.batch_size = page_response.batch_size
    job_response.error = page_response.error
