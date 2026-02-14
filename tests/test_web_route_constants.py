from hyperbrowser.client.managers.web_route_constants import (
    BATCH_FETCH_JOB_ROUTE_PREFIX,
    WEB_CRAWL_JOB_ROUTE_PREFIX,
)


def test_web_route_constants_match_expected_api_paths():
    assert BATCH_FETCH_JOB_ROUTE_PREFIX == "/web/batch-fetch"
    assert WEB_CRAWL_JOB_ROUTE_PREFIX == "/web/crawl"
