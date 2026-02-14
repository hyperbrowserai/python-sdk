from hyperbrowser.client.managers.web_route_constants import (
    BATCH_FETCH_JOB_ROUTE_PREFIX,
    WEB_FETCH_ROUTE_PATH,
    WEB_CRAWL_JOB_ROUTE_PREFIX,
    WEB_SEARCH_ROUTE_PATH,
)


def test_web_route_constants_match_expected_api_paths():
    assert BATCH_FETCH_JOB_ROUTE_PREFIX == "/web/batch-fetch"
    assert WEB_CRAWL_JOB_ROUTE_PREFIX == "/web/crawl"
    assert WEB_FETCH_ROUTE_PATH == "/web/fetch"
    assert WEB_SEARCH_ROUTE_PATH == "/web/search"
