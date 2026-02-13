import time
from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ...polling import (
    has_exceeded_max_wait,
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

        failures = 0
        page_fetch_start_time = time.monotonic()
        job_response = CrawlJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalCrawledPages=0,
            batchSize=100,
        )
        first_check = True
        while (
            first_check
            or job_response.current_page_batch < job_response.total_page_batches
        ):
            if has_exceeded_max_wait(page_fetch_start_time, max_wait_seconds):
                raise HyperbrowserError(
                    f"Timed out fetching all pages for crawl job {job_id} after {max_wait_seconds} seconds"
                )
            try:
                tmp_job_response = self.get(
                    job_start_resp.job_id,
                    GetCrawlJobParams(
                        page=job_response.current_page_batch + 1, batch_size=100
                    ),
                )
                if tmp_job_response.data:
                    job_response.data.extend(tmp_job_response.data)
                job_response.current_page_batch = tmp_job_response.current_page_batch
                job_response.total_crawled_pages = tmp_job_response.total_crawled_pages
                job_response.total_page_batches = tmp_job_response.total_page_batches
                job_response.batch_size = tmp_job_response.batch_size
                job_response.error = tmp_job_response.error
                failures = 0
                first_check = False
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to get crawl batch page {job_response.current_page_batch} for job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(0.5)

        return job_response
