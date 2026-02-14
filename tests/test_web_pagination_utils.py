from hyperbrowser.client.managers.web_pagination_utils import (
    initialize_paginated_job_response,
)
from hyperbrowser.models import BatchFetchJobResponse, WebCrawlJobResponse


def test_initialize_paginated_job_response_for_batch_fetch():
    response = initialize_paginated_job_response(
        model=BatchFetchJobResponse,
        job_id="job-1",
        status="completed",
    )

    assert response.job_id == "job-1"
    assert response.status == "completed"
    assert response.data == []
    assert response.current_page_batch == 0
    assert response.total_page_batches == 0
    assert response.total_pages == 0
    assert response.batch_size == 100


def test_initialize_paginated_job_response_for_web_crawl_with_custom_batch_size():
    response = initialize_paginated_job_response(
        model=WebCrawlJobResponse,
        job_id="job-2",
        status="running",
        batch_size=25,
    )

    assert response.job_id == "job-2"
    assert response.status == "running"
    assert response.data == []
    assert response.current_page_batch == 0
    assert response.total_page_batches == 0
    assert response.total_pages == 0
    assert response.batch_size == 25
