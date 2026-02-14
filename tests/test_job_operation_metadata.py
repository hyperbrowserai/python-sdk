from hyperbrowser.client.managers.job_operation_metadata import (
    BATCH_SCRAPE_OPERATION_METADATA,
    CRAWL_OPERATION_METADATA,
    EXTRACT_OPERATION_METADATA,
    SCRAPE_OPERATION_METADATA,
)


def test_batch_scrape_operation_metadata_values():
    assert BATCH_SCRAPE_OPERATION_METADATA.start_operation_name == "batch scrape start"
    assert (
        BATCH_SCRAPE_OPERATION_METADATA.status_operation_name == "batch scrape status"
    )
    assert BATCH_SCRAPE_OPERATION_METADATA.job_operation_name == "batch scrape job"
    assert (
        BATCH_SCRAPE_OPERATION_METADATA.start_error_message
        == "Failed to start batch scrape job"
    )
    assert (
        BATCH_SCRAPE_OPERATION_METADATA.operation_name_prefix == "batch scrape job "
    )


def test_scrape_operation_metadata_values():
    assert SCRAPE_OPERATION_METADATA.start_operation_name == "scrape start"
    assert SCRAPE_OPERATION_METADATA.status_operation_name == "scrape status"
    assert SCRAPE_OPERATION_METADATA.job_operation_name == "scrape job"
    assert SCRAPE_OPERATION_METADATA.start_error_message == "Failed to start scrape job"
    assert SCRAPE_OPERATION_METADATA.operation_name_prefix == "scrape job "


def test_crawl_operation_metadata_values():
    assert CRAWL_OPERATION_METADATA.start_operation_name == "crawl start"
    assert CRAWL_OPERATION_METADATA.status_operation_name == "crawl status"
    assert CRAWL_OPERATION_METADATA.job_operation_name == "crawl job"
    assert CRAWL_OPERATION_METADATA.start_error_message == "Failed to start crawl job"
    assert CRAWL_OPERATION_METADATA.operation_name_prefix == "crawl job "


def test_extract_operation_metadata_values():
    assert EXTRACT_OPERATION_METADATA.start_operation_name == "extract start"
    assert EXTRACT_OPERATION_METADATA.status_operation_name == "extract status"
    assert EXTRACT_OPERATION_METADATA.job_operation_name == "extract job"
    assert (
        EXTRACT_OPERATION_METADATA.start_error_message == "Failed to start extract job"
    )
    assert EXTRACT_OPERATION_METADATA.operation_name_prefix == "extract job "
