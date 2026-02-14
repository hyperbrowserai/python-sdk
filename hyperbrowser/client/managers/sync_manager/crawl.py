from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ...polling import (
    build_fetch_operation_name,
    build_operation_name,
    collect_paginated_results,
    ensure_started_job_id,
    poll_until_terminal_status,
    retry_operation,
)
from ..page_params_utils import build_page_batch_params
from ..job_pagination_utils import (
    build_job_paginated_page_merge_callback,
    initialize_job_paginated_response,
)
from ..serialization_utils import (
    serialize_model_dump_or_default,
    serialize_model_dump_to_dict,
)
from ..response_utils import parse_response_model
from ....models.crawl import (
    CrawlJobResponse,
    CrawlJobStatusResponse,
    GetCrawlJobParams,
    StartCrawlJobParams,
    StartCrawlJobResponse,
)


class CrawlManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        payload = serialize_model_dump_to_dict(
            params,
            error_message="Failed to serialize crawl start params",
        )
        response = self._client.transport.post(
            self._client._build_url("/crawl"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartCrawlJobResponse,
            operation_name="crawl start",
        )

    def get_status(self, job_id: str) -> CrawlJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=CrawlJobStatusResponse,
            operation_name="crawl status",
        )

    def get(
        self, job_id: str, params: Optional[GetCrawlJobParams] = None
    ) -> CrawlJobResponse:
        query_params = serialize_model_dump_or_default(
            params,
            default_factory=GetCrawlJobParams,
            error_message="Failed to serialize crawl get params",
        )
        response = self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}"),
            params=query_params,
        )
        return parse_response_model(
            response.data,
            model=CrawlJobResponse,
            operation_name="crawl job",
        )

    def start_and_wait(
        self,
        params: StartCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> CrawlJobResponse:
        job_start_resp = self.start(params)
        job_id = ensure_started_job_id(
            job_start_resp.job_id,
            error_message="Failed to start crawl job",
        )
        operation_name = build_operation_name("crawl job ", job_id)

        job_status = poll_until_terminal_status(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return retry_operation(
                operation_name=build_fetch_operation_name(operation_name),
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = initialize_job_paginated_response(
            model=CrawlJobResponse,
            job_id=job_id,
            status=job_status,
            total_counter_alias="totalCrawledPages",
        )

        collect_paginated_results(
            operation_name=operation_name,
            get_next_page=lambda page: self.get(
                job_start_resp.job_id,
                params=build_page_batch_params(
                    GetCrawlJobParams,
                    page=page,
                ),
            ),
            get_current_page_batch=lambda page_response: (
                page_response.current_page_batch
            ),
            get_total_page_batches=lambda page_response: (
                page_response.total_page_batches
            ),
            on_page_success=build_job_paginated_page_merge_callback(
                job_response=job_response,
                total_counter_attr="total_crawled_pages",
            ),
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response
