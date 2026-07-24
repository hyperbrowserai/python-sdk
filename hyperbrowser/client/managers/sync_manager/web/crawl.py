import time
from typing import Optional, Union

from hyperbrowser.client._request import (
    dump_request,
    dump_request_with_fetch_schemas,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    StartWebCrawlJobParams,
    StartWebCrawlJobResponse,
    WebCrawlJobStatusResponse,
    GetWebCrawlJobParams,
    WebCrawlJobResponse,
    WebCrawlJobStatus,
    POLLING_ATTEMPTS,
)
from hyperbrowser.types import (
    GetWebCrawlJobParams as GetWebCrawlJobParamsDict,
    StartWebCrawlJobParams as StartWebCrawlJobParamsDict,
)


class WebCrawlManager:
    def __init__(self, client):
        self._client = client

    def start(
        self,
        params: Union[StartWebCrawlJobParamsDict, StartWebCrawlJobParams],
    ) -> StartWebCrawlJobResponse:
        response = self._client.transport.post(
            self._client._build_url("/web/crawl"),
            data=dump_request_with_fetch_schemas(params, StartWebCrawlJobParams),
        )
        return StartWebCrawlJobResponse(**response.data)

    def get_status(self, job_id: str) -> WebCrawlJobStatusResponse:
        response = self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}/status")
        )
        return WebCrawlJobStatusResponse(**response.data)

    def get(
        self,
        job_id: str,
        params: Optional[Union[GetWebCrawlJobParamsDict, GetWebCrawlJobParams]] = None,
    ) -> WebCrawlJobResponse:
        if params is None:
            params = GetWebCrawlJobParams()
        response = self._client.transport.get(
            self._client._build_url(f"/web/crawl/{job_id}"),
            params=dump_request(params, GetWebCrawlJobParams),
        )
        return WebCrawlJobResponse(**response.data)

    def start_and_wait(
        self,
        params: Union[StartWebCrawlJobParamsDict, StartWebCrawlJobParams],
        return_all_pages: bool = True,
    ) -> WebCrawlJobResponse:
        job_start_resp = self.start(params)
        job_id = job_start_resp.job_id
        if not job_id:
            raise HyperbrowserError("Failed to start web crawl job")

        job_status: WebCrawlJobStatus = "pending"
        failures = 0
        while True:
            try:
                job_status_resp = self.get_status(job_id)
                job_status = job_status_resp.status
                if job_status == "completed" or job_status == "failed":
                    break
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to poll web crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(2)

        failures = 0
        if not return_all_pages:
            while True:
                try:
                    return self.get(job_id)
                except Exception as e:
                    failures += 1
                    if failures >= POLLING_ATTEMPTS:
                        raise HyperbrowserError(
                            f"Failed to get web crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                        )
                time.sleep(0.5)

        failures = 0
        job_response = WebCrawlJobResponse(
            jobId=job_id,
            status=job_status,
            data=[],
            currentPageBatch=0,
            totalPageBatches=0,
            totalPages=0,
            batchSize=100,
        )
        first_check = True

        while (
            first_check
            or job_response.current_page_batch < job_response.total_page_batches
        ):
            try:
                tmp_job_response = self.get(
                    job_id,
                    params=GetWebCrawlJobParams(
                        page=job_response.current_page_batch + 1, batch_size=100
                    ),
                )
                if tmp_job_response.data:
                    job_response.data.extend(tmp_job_response.data)
                job_response.current_page_batch = tmp_job_response.current_page_batch
                job_response.total_pages = tmp_job_response.total_pages
                job_response.total_page_batches = tmp_job_response.total_page_batches
                job_response.batch_size = tmp_job_response.batch_size
                job_response.error = tmp_job_response.error
                failures = 0
                first_check = False
            except Exception as e:
                failures += 1
                if failures >= POLLING_ATTEMPTS:
                    raise HyperbrowserError(
                        f"Failed to get batch page {job_response.current_page_batch} for web crawl job {job_id} after {POLLING_ATTEMPTS} attempts: {e}"
                    )
            time.sleep(0.5)

        return job_response
