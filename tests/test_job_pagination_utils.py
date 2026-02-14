from hyperbrowser.client.managers.job_pagination_utils import (
    initialize_job_paginated_response,
    merge_job_paginated_page_response,
)
from hyperbrowser.models.crawl import CrawlJobResponse
from hyperbrowser.models.scrape import BatchScrapeJobResponse


def test_initialize_job_paginated_response_for_batch_scrape():
    response = initialize_job_paginated_response(
        model=BatchScrapeJobResponse,
        job_id="job-1",
        status="completed",
        total_counter_alias="totalScrapedPages",
    )

    assert response.job_id == "job-1"
    assert response.status == "completed"
    assert response.data == []
    assert response.current_page_batch == 0
    assert response.total_page_batches == 0
    assert response.total_scraped_pages == 0
    assert response.batch_size == 100


def test_initialize_job_paginated_response_for_crawl_with_custom_batch_size():
    response = initialize_job_paginated_response(
        model=CrawlJobResponse,
        job_id="job-2",
        status="running",
        total_counter_alias="totalCrawledPages",
        batch_size=25,
    )

    assert response.job_id == "job-2"
    assert response.status == "running"
    assert response.data == []
    assert response.current_page_batch == 0
    assert response.total_page_batches == 0
    assert response.total_crawled_pages == 0
    assert response.batch_size == 25


def test_merge_job_paginated_page_response_updates_totals_and_error():
    job_response = initialize_job_paginated_response(
        model=CrawlJobResponse,
        job_id="job-2",
        status="running",
        total_counter_alias="totalCrawledPages",
    )
    page_response = CrawlJobResponse(
        jobId="job-2",
        status="running",
        data=[],
        currentPageBatch=3,
        totalPageBatches=9,
        totalCrawledPages=21,
        batchSize=50,
        error="partial failure",
    )

    merge_job_paginated_page_response(
        job_response,
        page_response,
        total_counter_attr="total_crawled_pages",
    )

    assert job_response.current_page_batch == 3
    assert job_response.total_page_batches == 9
    assert job_response.total_crawled_pages == 21
    assert job_response.batch_size == 50
    assert job_response.error == "partial failure"
