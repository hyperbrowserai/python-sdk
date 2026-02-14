from typing import Type, TypeVar

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
