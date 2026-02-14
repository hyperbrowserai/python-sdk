from dataclasses import dataclass


@dataclass(frozen=True)
class JobOperationMetadata:
    start_operation_name: str
    status_operation_name: str
    job_operation_name: str
    start_error_message: str
    operation_name_prefix: str


BATCH_SCRAPE_OPERATION_METADATA = JobOperationMetadata(
    start_operation_name="batch scrape start",
    status_operation_name="batch scrape status",
    job_operation_name="batch scrape job",
    start_error_message="Failed to start batch scrape job",
    operation_name_prefix="batch scrape job ",
)

SCRAPE_OPERATION_METADATA = JobOperationMetadata(
    start_operation_name="scrape start",
    status_operation_name="scrape status",
    job_operation_name="scrape job",
    start_error_message="Failed to start scrape job",
    operation_name_prefix="scrape job ",
)

CRAWL_OPERATION_METADATA = JobOperationMetadata(
    start_operation_name="crawl start",
    status_operation_name="crawl status",
    job_operation_name="crawl job",
    start_error_message="Failed to start crawl job",
    operation_name_prefix="crawl job ",
)

EXTRACT_OPERATION_METADATA = JobOperationMetadata(
    start_operation_name="extract start",
    status_operation_name="extract status",
    job_operation_name="extract job",
    start_error_message="Failed to start extract job",
    operation_name_prefix="extract job ",
)
