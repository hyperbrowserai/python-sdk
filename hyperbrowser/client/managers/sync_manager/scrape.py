import time
from typing import Optional

from hyperbrowser.models.consts import POLLING_ATTEMPTS
from ....models.scrape import (
    BatchScrapeJobResponse,
    GetBatchScrapeJobParams,
    ScrapeJobResponse,
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

    def get(
        self, job_id: str, params: GetBatchScrapeJobParams = GetBatchScrapeJobParams()
    ) -> BatchScrapeJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/batch/{job_id}"), params=params.__dict__
        )
        return BatchScrapeJobResponse(**response.data)

    def start_and_wait(
        self, params: StartBatchScrapeJobParams, return_all_pages: bool = True
    ) -> BatchScrapeJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start batch scrape job")

        job_response: BatchScrapeJobResponse
        failures = 0
        while True:
            try:
                job_response = self.get(
                    job_id, params=GetBatchScrapeJobParams(batch_size=1)
                )
                if (
                    job_response.status == "completed"
                    or job_response.status == "failed"
                ):
                    break
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll batch scrape job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
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
                            f"Failed to get batch scrape job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                        )
                time.sleep(0.5)

        failures = 0
        job_response.current_page_batch = 0
        job_response.data = []
        while job_response.current_page_batch < job_response.total_page_batches:
            try:
                tmp_job_response = self.get(
                    job_start_resp.job_id,
                    GetBatchScrapeJobParams(
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
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to get batch page {job_response.current_page_batch} for job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(0.5)

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

    def get(self, job_id: str) -> ScrapeJobResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/scrape/{job_id}")
        )
        return ScrapeJobResponse(**response.data)

    def start_and_wait(self, params: StartScrapeJobParams) -> ScrapeJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start scrape job")

        failures = 0
        while True:
            try:
                job_response = self.get(job_id)
                if (
                    job_response.status == "completed"
                    or job_response.status == "failed"
                ):
                    return job_response
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll scrape job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)
