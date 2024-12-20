import asyncio
from typing import Optional
from ....models.scrape import (
    ScrapeJobResponse,
    StartScrapeJobParams,
    StartScrapeJobResponse,
)
from ....exceptions import HyperbrowserError


class ScrapeManager:
    def __init__(self, client):
        self._client = client

    async def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        response = await self._client.transport.post(
            self._client._build_url("/scrape"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartScrapeJobResponse(**response.data)

    async def get(self, job_id: str) -> ScrapeJobResponse:
        response = await self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return ScrapeJobResponse(**response.data)

    async def start_and_wait(self, params: StartScrapeJobParams) -> ScrapeJobResponse:
        job_start_resp = await self.start(params)
        if not job_start_resp.job_id:
            raise HyperbrowserError("Failed to start scrape job")
        while True:
            job_response = await self.get(job_start_resp.job_id)
            if job_response.status == "completed" or job_response.status == "failed":
                return job_response
            await asyncio.sleep(2)
