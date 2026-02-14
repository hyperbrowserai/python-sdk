from dataclasses import dataclass


@dataclass(frozen=True)
class WebOperationMetadata:
    start_operation_name: str
    status_operation_name: str
    job_operation_name: str
    start_error_message: str
    operation_name_prefix: str


BATCH_FETCH_OPERATION_METADATA = WebOperationMetadata(
    start_operation_name="batch fetch start",
    status_operation_name="batch fetch status",
    job_operation_name="batch fetch job",
    start_error_message="Failed to start batch fetch job",
    operation_name_prefix="batch fetch job ",
)

WEB_CRAWL_OPERATION_METADATA = WebOperationMetadata(
    start_operation_name="web crawl start",
    status_operation_name="web crawl status",
    job_operation_name="web crawl job",
    start_error_message="Failed to start web crawl job",
    operation_name_prefix="web crawl job ",
)
