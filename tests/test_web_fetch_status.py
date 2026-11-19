from hyperbrowser.models import (
    BatchFetchJobResponse,
    FetchResponse,
    WebCrawlJobResponse,
)


def test_fetch_response_reports_the_http_status_and_final_url():
    response = FetchResponse(
        **{
            "jobId": "job-1",
            "status": "completed",
            "data": {
                "statusCode": 403,
                "finalUrl": "https://example.com/blocked",
                "markdown": "Access denied",
                "metadata": {"sourceURL": "https://example.com/old"},
            },
        }
    )

    assert response.data.status_code == 403
    assert response.data.final_url == "https://example.com/blocked"
    assert response.data.model_dump(by_alias=True, exclude_none=True) == {
        "statusCode": 403,
        "finalUrl": "https://example.com/blocked",
        "markdown": "Access denied",
        "metadata": {"sourceURL": "https://example.com/old"},
    }


def test_fetch_response_without_the_status_fields_still_parses():
    # The API can omit both fields.
    response = FetchResponse(
        **{"jobId": "job-1", "status": "completed", "data": {"markdown": "# Title"}}
    )

    assert response.data.markdown == "# Title"
    assert response.data.status_code is None
    assert response.data.final_url is None


def test_batch_fetch_and_crawl_pages_report_the_http_status_and_final_url():
    page = {
        "url": "https://example.com/old",
        "status": "completed",
        "statusCode": 404,
        "finalUrl": "https://example.com/not-found",
        "markdown": "Not found",
    }
    job = {
        "jobId": "job-1",
        "status": "completed",
        "data": [page, {"url": "https://example.com/", "status": "completed"}],
        "totalPages": 2,
        "totalPageBatches": 1,
        "currentPageBatch": 1,
        "batchSize": 100,
    }

    for response in (BatchFetchJobResponse(**job), WebCrawlJobResponse(**job)):
        reported, omitted = response.data
        assert reported.status_code == 404
        assert reported.final_url == "https://example.com/not-found"
        assert omitted.status_code is None
        assert omitted.final_url is None
