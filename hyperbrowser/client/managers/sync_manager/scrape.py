import time
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

    def start(self, params: StartScrapeJobParams) -> StartScrapeJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/scrape"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartScrapeJobResponse(**response.data)

    def get(self, job_id: str) -> ScrapeJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return ScrapeJobResponse(**response.data)

    def start_and_wait(self, params: StartScrapeJobParams) -> ScrapeJobResponse:
        job_start_resp = self.start(params)
        if not job_start_resp.job_id:
            raise HyperbrowserError("Failed to start scrape job")
        while True:
            job_response = self.get(job_start_resp.job_id)
            if job_response.status == "completed" or job_response.status == "failed":
                return job_response
            time.sleep(2)
