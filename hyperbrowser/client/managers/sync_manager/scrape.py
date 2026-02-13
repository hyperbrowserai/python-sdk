from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ...polling import (
    build_fetch_operation_name,
    collect_paginated_results,
    poll_until_terminal_status,
    retry_operation,
    wait_for_job_result,
)
from ....models.scrape import (
    BatchScrapeJobResponse,
    BatchScrapeJobStatusResponse,
    GetBatchScrapeJobParams,
    ScrapeJobResponse,
    ScrapeJobStatusResponse,
    StartBatchScrapeJobParams,
    StartBatchScrapeJobResponse,
    StartScrapeJobParams,
    StartScrapeJobResponse,
)
from ....exceptions import HyperbrowserError


class BatchScrapeManager:
    def __init__(self, client):
        self._client = client

    def start(self, params: StartBatchScrapeJobParams) -> StartBatchScrapeJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/scrape/batch"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartBatchScrapeJobResponse(**response.data)

    def get_status(self, job_id: str) -> BatchScrapeJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}/status")
        )
        return BatchScrapeJobStatusResponse(**response.data)

    def get(
        self, job_id: str, params: Optional[GetBatchScrapeJobParams] = None
    ) -> BatchScrapeJobResponse:
        params_obj = params or GetBatchScrapeJobParams()
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return BatchScrapeJobResponse(**response.data)

    def start_and_wait(
        self,
        params: StartBatchScrapeJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BatchScrapeJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start batch scrape job")

        job_status = poll_until_terminal_status(
            operation_name=f"batch scrape job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return retry_operation(
                operation_name=build_fetch_operation_name(f"batch scrape job {job_id}"),
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = BatchScrapeJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalScrapedPages=0,
            batchSize=100,
        )

        def merge_page_response(page_response: BatchScrapeJobResponse) -> None:
            if page_response.data:
                job_response.data.extend(page_response.data)
            job_response.current_page_batch = page_response.current_page_batch
            job_response.total_scraped_pages = page_response.total_scraped_pages
            job_response.total_page_batches = page_response.total_page_batches
            job_response.batch_size = page_response.batch_size
            job_response.error = page_response.error

        collect_paginated_results(
            operation_name=f"batch scrape job {job_id}",
            get_next_page=lambda page: self.get(
                job_id,
                params=GetBatchScrapeJobParams(page=page, batch_size=100),
            ),
            get_current_page_batch=lambda page_response: (
                page_response.current_page_batch
            ),
            get_total_page_batches=lambda page_response: (
                page_response.total_page_batches
            ),
            on_page_success=merge_page_response,
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response


class ScrapeManager:
    def __init__(self, client):
        self._client = client
        self.batch = BatchScrapeManager(client)

    def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/scrape"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartScrapeJobResponse(**response.data)

    def get_status(self, job_id: str) -> ScrapeJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}/status")
        )
        return ScrapeJobStatusResponse(**response.data)

    def get(self, job_id: str) -> ScrapeJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return ScrapeJobResponse(**response.data)

    def start_and_wait(
        self,
        params: StartScrapeJobParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ScrapeJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start scrape job")

        return wait_for_job_result(
            operation_name=f"scrape job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
