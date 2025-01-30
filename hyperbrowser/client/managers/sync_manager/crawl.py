import time
from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
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

    def start(self, params: StartCrawlJobParams) -> StartCrawlJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/crawl"),
            data=params.model_dump(exclude_none=True, by_alias=True),
        )
        return StartCrawlJobResponse(**response.data)

    def get(
        self, job_id: str, params: GetCrawlJobParams = GetCrawlJobParams()
    ) -> CrawlJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/crawl/{job_id}"), params=params.__dict__
        )
        return CrawlJobResponse(**response.data)

    def start_and_wait(
        self, params: StartCrawlJobParams, return_all_pages: bool = True
    ) -> CrawlJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start crawl job")

        job_response: CrawlJobResponse
        failures = 0
        while True:
            try:
                job_response = self.get(
                    job_id,
                    params=GetCrawlJobParams(batch_size=1),
                )
                if (
                    job_response.status == "completed"
                    or job_response.status == "failed"
                ):
                    break
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)

        failures = 0
        if not return_all_pages:
            while True:
                try:
                    job_response = self.get(job_id)
                    return job_response
                except Exception as e:
                    failures += 1
                    if failures >= POLLING_ATTEMPTS:
                        raise HyperbrowserError(
                            f"Failed to get crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                        )
                time.sleep(0.5)

        failures = 0
        job_response.current_page_batch = 0
        job_response.data = []
        while job_response.current_page_batch < job_response.total_page_batches:
            try:
                tmp_job_response = self.get(
                    job_id,
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
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to get crawl batch page {job_response.current_page_batch} for job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(0.5)

        return job_response
