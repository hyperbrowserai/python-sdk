from hyperbrowser.client.managers.job_route_builders import (
    build_job_route,
    build_job_status_route,
)


def test_build_job_route_composes_job_route_path():
    assert build_job_route("/scrape", "job_123") == "/scrape/job_123"
    assert build_job_route("/web/crawl", "job_456") == "/web/crawl/job_456"


def test_build_job_status_route_composes_job_status_route_path():
    assert build_job_status_route("/scrape", "job_123") == "/scrape/job_123/status"
    assert (
        build_job_status_route("/web/crawl", "job_456")
        == "/web/crawl/job_456/status"
    )
