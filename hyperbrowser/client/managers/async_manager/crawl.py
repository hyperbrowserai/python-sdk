import asyncio
from typing import Optional
from ....models.crawl import (
    CrawlJobResponse,
    GetCrawlJobParams,
    StartCrawlJobParams,
    StartCrawlJobResponse,
)
from ....exceptions import HyperbrowserError


class CrawlManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        response = await self._client.transport.post(
            self._client._build_url("/crawl"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartCrawlJobResponse(**response.data)

    async def get(
        self, job_id: str, params: GetCrawlJobParams = GetCrawlJobParams()
    ) -> CrawlJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}"), params=params.__dict__
        )
        return CrawlJobResponse(**response.data)

    async def start_and_wait(
        self, params: StartCrawlJobParams, return_all_pages: bool = True
    ) -> CrawlJobResponse:
        job_start_resp = await self.start(params)
        if not job_start_resp.job_id:
            raise HyperbrowserError("Failed to start crawl job")

        job_response: CrawlJobResponse
        while True:
            job_response = await self.get(job_start_resp.job_id)
            if job_response.status == "completed" or job_response.status == "failed":
                break
            await asyncio.sleep(2)

        if not return_all_pages:
            return job_response

        while job_response.current_page_batch < job_response.total_page_batches:
            tmp_job_response = await self.get(
                job_start_resp.job_id,
                GetCrawlJobParams(page=job_response.current_page_batch + 1),
            )
            if tmp_job_response.data:
                job_response.data.extend(tmp_job_response.data)
            job_response.current_page_batch = tmp_job_response.current_page_batch
            job_response.total_crawled_pages = tmp_job_response.total_crawled_pages
            job_response.total_page_batches = tmp_job_response.total_page_batches
            job_response.batch_size = tmp_job_response.batch_size
            await asyncio.sleep(0.5)
        return job_response
