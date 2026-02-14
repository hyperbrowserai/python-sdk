from hyperbrowser.client.managers.web_operation_metadata import (
    BATCH_FETCH_OPERATION_METADATA,
    WEB_CRAWL_OPERATION_METADATA,
)


def test_batch_fetch_operation_metadata_values():
    assert BATCH_FETCH_OPERATION_METADATA.start_operation_name == "batch fetch start"
    assert BATCH_FETCH_OPERATION_METADATA.status_operation_name == "batch fetch status"
    assert BATCH_FETCH_OPERATION_METADATA.job_operation_name == "batch fetch job"
    assert (
        BATCH_FETCH_OPERATION_METADATA.start_error_message
        == "Failed to start batch fetch job"
    )
    assert BATCH_FETCH_OPERATION_METADATA.operation_name_prefix == "batch fetch job "


def test_web_crawl_operation_metadata_values():
    assert WEB_CRAWL_OPERATION_METADATA.start_operation_name == "web crawl start"
    assert WEB_CRAWL_OPERATION_METADATA.status_operation_name == "web crawl status"
    assert WEB_CRAWL_OPERATION_METADATA.job_operation_name == "web crawl job"
    assert (
        WEB_CRAWL_OPERATION_METADATA.start_error_message
        == "Failed to start web crawl job"
    )
    assert WEB_CRAWL_OPERATION_METADATA.operation_name_prefix == "web crawl job "
