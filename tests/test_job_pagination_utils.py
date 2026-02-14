from hyperbrowser.client.managers.job_pagination_utils import (
    build_job_paginated_page_merge_callback,
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


def test_build_job_paginated_page_merge_callback_merges_values():
    job_response = initialize_job_paginated_response(
        model=BatchScrapeJobResponse,
        job_id="job-3",
        status="running",
        total_counter_alias="totalScrapedPages",
    )
    page_response = BatchScrapeJobResponse(
        jobId="job-3",
        status="running",
        data=[],
        currentPageBatch=1,
        totalPageBatches=5,
        totalScrapedPages=6,
        batchSize=30,
        error=None,
    )
    merge_callback = build_job_paginated_page_merge_callback(
        job_response=job_response,
        total_counter_attr="total_scraped_pages",
    )

    merge_callback(page_response)

    assert job_response.current_page_batch == 1
    assert job_response.total_page_batches == 5
    assert job_response.total_scraped_pages == 6
    assert job_response.batch_size == 30
