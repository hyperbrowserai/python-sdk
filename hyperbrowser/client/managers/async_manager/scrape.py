from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ...polling import (
    build_fetch_operation_name,
    build_operation_name,
    collect_paginated_results_async,
    ensure_started_job_id,
    poll_until_terminal_status_async,
    retry_operation_async,
    wait_for_job_result_async,
)
from ..response_utils import parse_response_model
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


class BatchScrapeManager:
    def __init__(self, client):
        self._client = client

    async def start(
        self, params: StartBatchScrapeJobParams
    ) -> StartBatchScrapeJobResponse:
        try:
            payload = params.model_dump(exclude_none=True, by_alias=True)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to serialize batch scrape start params",
                original_error=exc,
            ) from exc
        if type(payload) is not dict:
            raise HyperbrowserError("Failed to serialize batch scrape start params")
        response = await self._client.transport.post(
            self._client._build_url("/scrape/batch"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartBatchScrapeJobResponse,
            operation_name="batch scrape start",
        )

    async def get_status(self, job_id: str) -> BatchScrapeJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=BatchScrapeJobStatusResponse,
            operation_name="batch scrape status",
        )

    async def get(
        self, job_id: str, params: Optional[GetBatchScrapeJobParams] = None
    ) -> BatchScrapeJobResponse:
        params_obj = params or GetBatchScrapeJobParams()
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return parse_response_model(
            response.data,
            model=BatchScrapeJobResponse,
            operation_name="batch scrape job",
        )

    async def start_and_wait(
        self,
        params: StartBatchScrapeJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> BatchScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id = ensure_started_job_id(
            job_start_resp.job_id,
            error_message="Failed to start batch scrape job",
        )
        operation_name = build_operation_name("batch scrape job ", job_id)

        job_status = await poll_until_terminal_status_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
        )

        if not return_all_pages:
            return await retry_operation_async(
                operation_name=build_fetch_operation_name(operation_name),
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

        await collect_paginated_results_async(
            operation_name=operation_name,
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

    async def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        try:
            payload = params.model_dump(exclude_none=True, by_alias=True)
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to serialize scrape start params",
                original_error=exc,
            ) from exc
        if type(payload) is not dict:
            raise HyperbrowserError("Failed to serialize scrape start params")
        response = await self._client.transport.post(
            self._client._build_url("/scrape"),
            data=payload,
        )
        return parse_response_model(
            response.data,
            model=StartScrapeJobResponse,
            operation_name="scrape start",
        )

    async def get_status(self, job_id: str) -> ScrapeJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}/status")
        )
        return parse_response_model(
            response.data,
            model=ScrapeJobStatusResponse,
            operation_name="scrape status",
        )

    async def get(self, job_id: str) -> ScrapeJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return parse_response_model(
            response.data,
            model=ScrapeJobResponse,
            operation_name="scrape job",
        )

    async def start_and_wait(
        self,
        params: StartScrapeJobParams,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
        max_status_failures: int = POLLING_ATTEMPTS,
    ) -> ScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id = ensure_started_job_id(
            job_start_resp.job_id,
            error_message="Failed to start scrape job",
        )
        operation_name = build_operation_name("scrape job ", job_id)

        return await wait_for_job_result_async(
            operation_name=operation_name,
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            fetch_result=lambda: self.get(job_id),
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            max_status_failures=max_status_failures,
            fetch_max_attempts=POLLING_ATTEMPTS,
            fetch_retry_delay_seconds=0.5,
        )
