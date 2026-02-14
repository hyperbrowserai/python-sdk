from hyperbrowser.client.managers.job_route_constants import (
    BATCH_SCRAPE_JOB_ROUTE_PREFIX,
    CRAWL_JOB_ROUTE_PREFIX,
    EXTRACT_JOB_ROUTE_PREFIX,
    SCRAPE_JOB_ROUTE_PREFIX,
)


def test_job_route_constants_match_expected_api_paths():
    assert BATCH_SCRAPE_JOB_ROUTE_PREFIX == "/scrape/batch"
    assert SCRAPE_JOB_ROUTE_PREFIX == "/scrape"
    assert CRAWL_JOB_ROUTE_PREFIX == "/crawl"
    assert EXTRACT_JOB_ROUTE_PREFIX == "/extract"
