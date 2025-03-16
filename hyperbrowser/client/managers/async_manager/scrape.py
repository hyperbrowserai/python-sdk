import asyncio
from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ....models.scrape import (
    BatchScrapeJobResponse,
    BatchScrapeJobStatusResponse,
    GetBatchScrapeJobParams,
    ScrapeJobResponse,
    ScrapeJobStatus,
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

    async def start(
        self, params: StartBatchScrapeJobParams
    ) -> StartBatchScrapeJobResponse:
        response = await self._client.transport.post(
            self._client._build_url("/scrape/batch"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartBatchScrapeJobResponse(**response.data)

    async def get_status(self, job_id: str) -> BatchScrapeJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}/status")
        )
        return BatchScrapeJobStatusResponse(**response.data)

    async def get(
        self, job_id: str, params: GetBatchScrapeJobParams = GetBatchScrapeJobParams()
    ) -> BatchScrapeJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}"),
            params=params.model_dump(exclude_none=True, by_alias=True),
        )
        return BatchScrapeJobResponse(**response.data)

    async def start_and_wait(
        self, params: StartBatchScrapeJobParams, return_all_pages: bool = True
    ) -> BatchScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start batch scrape job")

        job_status: ScrapeJobStatus = "pending"
        failures = 0
        while True:
            try:
                job_status_resp = await self.get_status(job_id)
                job_status = job_status_resp.status
                if job_status == "completed" or job_status == "failed":
                    break
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll batch scrape job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(2)

        failures = 0
        if not return_all_pages:
            while True:
                try:
                    return await self.get(job_id)
                except Exception as e:
                    failures += 1
                    if failures >= POLLING_ATTEMPTS:
                        raise HyperbrowserError(
                            f"Failed to get batch scrape job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                        )
                await asyncio.sleep(0.5)

        failures = 0
        job_response = BatchScrapeJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalScrapedPages=0,
            batchSize=100,
        )
        first_check = True

        while (
            first_check
            or job_response.current_page_batch < job_response.total_page_batches
        ):
            try:
                tmp_job_response = await self.get(
                    job_id,
                    params=GetBatchScrapeJobParams(
                        page=job_response.current_page_batch + 1, batch_size=100
                    ),
                )
                if tmp_job_response.data:
                    job_response.data.extend(tmp_job_response.data)
                job_response.current_page_batch = tmp_job_response.current_page_batch
                job_response.total_scraped_pages = tmp_job_response.total_scraped_pages
                job_response.total_page_batches = tmp_job_response.total_page_batches
                job_response.batch_size = tmp_job_response.batch_size
                failures = 0
                first_check = False
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to get batch page {job_response.current_page_batch} for job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(0.5)

        return job_response


class ScrapeManager:
    def __init__(self, client):
        self._client = client
        self.batch = BatchScrapeManager(client)

    async def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        response = await self._client.transport.post(
            self._client._build_url("/scrape"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartScrapeJobResponse(**response.data)

    async def get_status(self, job_id: str) -> ScrapeJobStatusResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}/status")
        )
        return ScrapeJobStatusResponse(**response.data)

    async def get(self, job_id: str) -> ScrapeJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return ScrapeJobResponse(**response.data)

    async def start_and_wait(self, params: StartScrapeJobParams) -> ScrapeJobResponse:
        job_start_resp = await self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start scrape job")

        failures = 0
        while True:
            try:
                job_status_resp = await self.get_status(job_id)
                job_status = job_status_resp.status
                if job_status == "completed" or job_status == "failed":
                    return await self.get(job_id)
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll scrape job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            await asyncio.sleep(2)
