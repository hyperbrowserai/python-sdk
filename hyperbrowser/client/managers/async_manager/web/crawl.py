from typing import Optional

from hyperbrowser.models import (
    StartWebCrawlJobParams,
    StartWebCrawlJobResponse,
    WebCrawlJobStatusResponse,
    GetWebCrawlJobParams,
    WebCrawlJobResponse,
    POLLING_ATTEMPTS,
)
from hyperbrowser.exceptions import HyperbrowserError
from ....polling import (
    collect_paginated_results_async,
    poll_until_terminal_status_async,
    retry_operation_async,
)
from ....schema_utils import inject_web_output_schemas


class WebCrawlManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartWebCrawlJobParams) -> StartWebCrawlJobResponse:
        payload = params.model_dump(exclude_none=True, by_alias=True)
        inject_web_output_schemas(
            payload, params.outputs.formats if params.outputs else None
        )

        response = await self._client.transport.post(
            self._client._build_url("/web/crawl"),
            data=payload,
        )
        return StartWebCrawlJobResponse(**response.data)

    async def get_status(self, job_id: str) -> WebCrawlJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}/status")
        )
        return WebCrawlJobStatusResponse(**response.data)

    async def get(
        self, job_id: str, params: Optional[GetWebCrawlJobParams] = None
    ) -> WebCrawlJobResponse:
        params_obj = params or GetWebCrawlJobParams()
        response = await self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}"),
            params=params_obj.model_dump(exclude_none=True, by_alias=True),
        )
        return WebCrawlJobResponse(**response.data)

    async def start_and_wait(
        self,
        params: StartWebCrawlJobParams,
        return_all_pages: bool = True,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: Optional[float] = 600.0,
    ) -> WebCrawlJobResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start web crawl job")

        job_status = await poll_until_terminal_status_async(
            operation_name=f"web crawl job {job_id}",
            get_status=lambda: self.get_status(job_id).status,
            is_terminal_status=lambda status: status in {"completed", "failed"},
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
        )

        if not return_all_pages:
            return await retry_operation_async(
                operation_name=f"Fetching web crawl job {job_id}",
                operation=lambda: self.get(job_id),
                max_attempts=POLLING_ATTEMPTS,
                retry_delay_seconds=0.5,
            )

        job_response = WebCrawlJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalPages=0,
            batchSize=100,
        )

        def merge_page_response(page_response: WebCrawlJobResponse) -> None:
            if page_response.data:
                job_response.data.extend(page_response.data)
            job_response.current_page_batch = page_response.current_page_batch
            job_response.total_pages = page_response.total_pages
            job_response.total_page_batches = page_response.total_page_batches
            job_response.batch_size = page_response.batch_size
            job_response.error = page_response.error

        await collect_paginated_results_async(
            operation_name=f"web crawl job {job_id}",
            get_next_page=lambda page: self.get(
                job_id,
                params=GetWebCrawlJobParams(page=page, batch_size=100),
            ),
            get_current_page_batch=lambda page_response: page_response.current_page_batch,
            get_total_page_batches=lambda page_response: page_response.total_page_batches,
            on_page_success=merge_page_response,
            max_wait_seconds=max_wait_seconds,
            max_attempts=POLLING_ATTEMPTS,
            retry_delay_seconds=0.5,
        )

        return job_response
