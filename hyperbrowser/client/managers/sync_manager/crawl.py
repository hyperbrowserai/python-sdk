from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ...polling import (
    collect_paginated_results,
    poll_until_terminal_status,
    retry_operation,
)
from ....models.crawl import (
    CrawlJobResponse,
    CrawlJobStatusResponse,
    GetCrawlJobParams,
    StartCrawlJobParams,
    StartCrawlJobResponse,
)
from ....exceptions import HyperbrowserError


class CrawlManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/crawl"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartCrawlJobResponse(**response.data)

    def get_status(self, job_id: str) -> CrawlJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}/status")
        )
        return CrawlJobStatusResponse(**response.data)

    def get(
        self, job_id: str, params: Optional[GetCrawlJobParams] = None
    ) -> CrawlJobResponse:
        params_obj = params or GetCrawlJobParams()
        response = self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return CrawlJobResponse(**response.data)

    def start_and_wait(
        self,
        params: StartCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> CrawlJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start crawl job")

        job_status = poll_until_terminal_status(
            operation_name=f"crawl job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )

        if not return_all_pages:
            return retry_operation(
                operation_name=f"Fetching crawl job {job_id}",
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = CrawlJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalCrawledPages=0,
            batchSize=100,
        )

        def merge_page_response(page_response: CrawlJobResponse) -> None:
            if page_response.data:
                job_response.data.extend(page_response.data)
            job_response.current_page_batch = page_response.current_page_batch
            job_response.total_crawled_pages = page_response.total_crawled_pages
            job_response.total_page_batches = page_response.total_page_batches
            job_response.batch_size = page_response.batch_size
            job_response.error = page_response.error

        collect_paginated_results(
            operation_name=f"crawl job {job_id}",
            get_next_page=lambda page: self.get(
                job_start_resp.job_id,
                GetCrawlJobParams(page=page, batch_size=100),
            ),
            get_current_page_batch=lambda page_response: page_response.current_page_batch,
            get_total_page_batches=lambda page_response: page_response.total_page_batches,
            on_page_success=merge_page_response,
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response
